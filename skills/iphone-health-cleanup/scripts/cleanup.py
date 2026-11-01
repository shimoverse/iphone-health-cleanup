#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review-first offloaded-app cleanup. No device dependency is imported for planning/tests."""
import argparse
import asyncio
import hashlib
import html
import importlib.metadata
import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PMD_VERSION = "11.49.0"
SCHEMA = 1
PROTECTED_CATEGORIES = {
    "authenticator", "password_manager", "crypto_exchange", "crypto_wallet",
    "payment_wallet", "digital_identity", "financial_tool",
}
CATEGORIES = PROTECTED_CATEGORIES | {"ordinary", "unknown"}
# A conservative second check, not a complete app-category database.
PROTECTED_HINT = re.compile(
    r"authenticator|\b2fas\b|\bauthy\b|\bduo mobile\b|wallet|metamask|"
    r"\bbase app\b|\bcoinbase\b|\bbinance\b|\bbingx\b|\bbitbns\b|"
    r"\bbitrue\b|\bblofin\b|\bmexc\b|\bkraken\b|\bkucoin\b|\bokx\b|"
    r"\bbybit\b|\bgemini\b|\bcrypto com\b|\bbitget\b|\bbitstamp\b|"
    r"\b1password\b|\bbitwarden\b|\blastpass\b|\bdashlane\b|\bkeeper\b|"
    r"\bkeepass\b|\benpass\b|\bnordpass\b|\bproton pass\b|\bstrongbox\b|"
    r"\broboform\b|\bpasswords\b|\btradingview\b|\bcoinmarketcap\b|"
    r"\bcoinstats\b|\bcrypto bubbles\b|\bcryptopanic\b|\bcash app\b|\bcurve\b"
)
BUNDLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,254}\Z")


class Refused(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def read_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refused("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_pairs)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".cleanup-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def normalize_apps(raw):
    if not isinstance(raw, dict):
        raise Refused("Device returned an invalid app lookup; stop without deleting.")
    apps = {}
    for bid, record in raw.items():
        if not isinstance(bid, str) or not BUNDLE_ID.fullmatch(bid) or not isinstance(record, dict):
            raise Refused("Invalid app identity in lookup.")
        if record.get("CFBundleIdentifier") != bid:
            raise Refused("Lookup key and app identity disagree: " + bid)
        name = record.get("CFBundleDisplayName") or record.get("CFBundleName") or bid
        if not isinstance(name, str) or len(name) > 500:
            raise Refused("Invalid app name: " + bid)
        demoted, placeholder = record.get("IsDemotedApp"), record.get("IsPlaceholder")
        flags_valid = all(v is None or type(v) is bool for v in (demoted, placeholder))
        if flags_valid and demoted is True and placeholder is True and record.get("ApplicationType") == "User":
            state = "offloaded"
        elif flags_valid and demoted in (None, False) and placeholder in (None, False):
            state = "installed"
        else:
            state = "uncertain"
        if name == bid:
            state = "uncertain"
        apps[bid] = {
            "bundle_id": bid, "name": name, "state": state,
            "application_type": record.get("ApplicationType"),
            "version": record.get("CFBundleShortVersionString"),
            "is_demoted": demoted, "is_placeholder": placeholder,
        }
    return apps


def protected_hint(app):
    text = re.sub(r"[^a-z0-9]+", " ", (app["name"] + " " + app["bundle_id"]).casefold())
    return bool(PROTECTED_HINT.search(text))


def validate_inventory(inv):
    if inv.get("schema") != SCHEMA or not isinstance(inv.get("device_id"), str) or not inv["device_id"]:
        raise Refused("Inventory lacks a valid schema/device identity.")
    if not isinstance(inv.get("apps"), dict):
        raise Refused("Inventory lacks apps.")
    for bid, app in inv["apps"].items():
        if not isinstance(bid, str) or not BUNDLE_ID.fullmatch(bid) or app.get("bundle_id") != bid:
            raise Refused("Invalid inventory identity.")
        # Re-derive state from source flags; an edited 'state' cannot enable deletion.
        raw = {bid: {"CFBundleIdentifier": bid, "CFBundleDisplayName": app["name"],
                     "ApplicationType": app["application_type"],
                     "CFBundleShortVersionString": app["version"],
                     "IsDemotedApp": app["is_demoted"], "IsPlaceholder": app["is_placeholder"]}}
        if normalize_apps(raw)[bid] != app:
            raise Refused("Inventory metadata is inconsistent: " + bid)


def build_plan(inv, decisions):
    validate_inventory(inv)
    supplied = decisions.get("apps", {})
    explicit_protected = decisions.get("protected_bundle_ids", [])
    if not isinstance(supplied, dict) or not isinstance(explicit_protected, list):
        raise Refused("Decisions must contain apps and an optional protected_bundle_ids list.")
    if any(not isinstance(x, str) or not BUNDLE_ID.fullmatch(x) for x in explicit_protected):
        raise Refused("Invalid protected app ID.")
    if set(supplied) - set(inv["apps"]):
        raise Refused("Decisions name apps outside this inventory.")
    rows = {}
    for bid, app in inv["apps"].items():
        d = supplied.get(bid, {"action": "review", "category": "unknown", "reason": "Not classified"})
        if not isinstance(d, dict) or set(d) != {"action", "category", "reason"}:
            raise Refused("Each decision needs exactly action, category, reason: " + bid)
        action, category, reason = d["action"], d["category"], d["reason"]
        if action not in {"keep", "delete", "review"} or category not in CATEGORIES:
            raise Refused("Invalid action/category: " + bid)
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise Refused("A concise identity/decision reason is required: " + bid)
        protected = bid in explicit_protected or category in PROTECTED_CATEGORIES or protected_hint(app)
        if action == "delete" and (protected or category != "ordinary" or app["state"] != "offloaded"):
            raise Refused("Deletion is not eligible: " + app["name"])
        if protected:
            action = "keep"
        elif app["state"] == "installed":
            action = "keep"
        rows[bid] = {"action": action, "category": category, "reason": reason, "protected": protected}
    payload = {
        "schema": SCHEMA, "created_at": now(), "inventory": inv,
        "decisions": rows, "protected_bundle_ids": sorted(set(explicit_protected)),
        "targets": sorted(b for b, d in rows.items() if d["action"] == "delete"),
    }
    return {"payload": payload, "sha256": digest(payload)}


def validate_plan(plan, approved_sha=None):
    if set(plan) != {"payload", "sha256"} or digest(plan["payload"]) != plan["sha256"]:
        raise Refused("Plan changed or has an invalid digest; regenerate and review it.")
    if approved_sha is not None and approved_sha != plan["sha256"]:
        raise Refused("Approval does not match this exact plan.")
    p = plan["payload"]
    if p.get("schema") != SCHEMA:
        raise Refused("Unsupported plan schema.")
    inv = p["inventory"]
    validate_inventory(inv)
    decisions = p["decisions"]
    if set(decisions) != set(inv["apps"]):
        raise Refused("Plan must account for every inventory app.")
    # Rebuild all decisions to enforce policy even if someone recomputed a digest.
    raw_decisions = {b: {k: d[k] for k in ("action", "category", "reason")} for b, d in decisions.items()}
    rebuilt = build_plan(inv, {"apps": raw_decisions, "protected_bundle_ids": p["protected_bundle_ids"]})["payload"]
    if rebuilt["decisions"] != decisions or rebuilt["targets"] != p["targets"]:
        raise Refused("Plan violates protected-app or target-list rules.")
    return p


def render_plan(plan):
    p = validate_plan(plan)
    def cell(value):
        text = html.escape(str(value)).replace("\n", " ").replace("\r", " ")
        return re.sub(r"([\\`*_{}\[\]()#!|])", r"\\\1", text)
    lines = ["# iPhone cleanup review", "", "No apps have been deleted by preparing this plan.", "",
             "Deletion removes the selected apps' local data. Review the exact Delete list before approving.", "",
             "Plan SHA-256: `" + plan["sha256"] + "`", ""]
    for action, title in (("delete", "Delete"), ("keep", "Keep"), ("review", "Needs clarification")):
        ids = [b for b, d in p["decisions"].items() if d["action"] == action]
        lines += ["## " + title + " (" + str(len(ids)) + ")", "", "| App | App ID | Reason |", "|---|---|---|"]
        for bid in sorted(ids, key=lambda b: p["inventory"]["apps"][b]["name"].casefold()):
            lines.append("| " + " | ".join(cell(x) for x in
                         (p["inventory"]["apps"][bid]["name"], bid, p["decisions"][bid]["reason"])) + " |")
        lines.append("")
    return "\n".join(lines)


class PmdDevice:
    """Only app lookup, disk-space reading and uninstall are exposed here."""
    def __init__(self, device_id, timeout=30):
        self.device_id, self.timeout = device_id, timeout
        self.lockdown = self.service = None

    async def __aenter__(self):
        if importlib.metadata.version("pymobiledevice3") != PMD_VERSION:
            raise Refused("Use the reviewed pymobiledevice3==" + PMD_VERSION + " environment.")
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.installation_proxy import InstallationProxyService
        try:
            self.lockdown = await asyncio.wait_for(create_using_usbmux(
                serial=self.device_id, connection_type="USB", autopair=False), self.timeout)
            if not self.lockdown.paired or self.lockdown.udid != self.device_id:
                raise Refused("The selected USB device must already trust this Mac. No automatic pairing performed.")
            self.service = InstallationProxyService(self.lockdown)
            await asyncio.wait_for(self.service.__aenter__(), self.timeout)
            return self
        except BaseException:
            await self.__aexit__(None, None, None)
            raise

    async def __aexit__(self, *args):
        for obj in (self.service, self.lockdown):
            if obj is not None:
                try:
                    await asyncio.wait_for(obj.close(), 5)
                except Exception:
                    pass

    async def read_apps(self, ids=None):
        raw = await asyncio.wait_for(self.service.get_apps(
            application_type="User", show_placeholders=True, bundle_identifiers=ids), self.timeout)
        if ids is not None and set(raw) - set(ids):
            raise Refused("Targeted lookup returned unexpected app identities.")
        return normalize_apps(raw)

    async def free_bytes(self):
        try:
            value = await asyncio.wait_for(self.lockdown.get_value(
                domain="com.apple.disk_usage", key="AmountDataAvailable"), self.timeout)
            return value if type(value) is int and value >= 0 else None
        except Exception:
            return None

    async def uninstall(self, bid):
        await asyncio.wait_for(self.service.uninstall(bid), self.timeout)


def require_device(p, device):
    if device.device_id != p["inventory"]["device_id"]:
        raise Refused("This plan belongs to a different device.")


def require_retained(p, apps, critical_only=False):
    expected = {b for b, d in p["decisions"].items()
                if d["action"] != "delete" and (not critical_only or d["protected"])}
    missing = expected - set(apps)
    if missing:
        raise Refused("Retained app missing from lookup; stop: " + ", ".join(sorted(missing)))


def require_guards(guards, apps):
    if set(guards) - set(apps):
        raise Refused("Verification anchor/protected app missing; stop without further deletions.")


async def confirm_absent(device, bid, attempts, interval, guards, p):
    consecutive = 0
    for attempt in range(attempts):
        apps = await device.read_apps([bid] + guards)
        require_guards(guards, apps)
        consecutive = consecutive + 1 if bid not in apps else 0
        if consecutive >= 2:
            return True
        if attempt + 1 < attempts:
            await asyncio.sleep(interval)
    return False


@contextmanager
def device_lock(device_id):
    import fcntl
    directory = Path(tempfile.gettempdir()) / ("iphone-cleanup-locks-" + str(os.getuid()))
    directory.mkdir(mode=0o700, exist_ok=True)
    stat = directory.lstat()
    if directory.is_symlink() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise Refused("Unsafe device lock directory.")
    path = directory / (hashlib.sha256(device_id.encode()).hexdigest() + ".lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refused("Another cleanup is already running for this device.")
        yield
    finally:
        os.close(fd)


class Journal:
    def __init__(self, path, plan):
        self.path, self.plan = Path(path), plan
        self.attempted = set()
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    raise Refused("Incomplete journal; inspect it before resuming.")
                if event.get("plan_sha256") != plan["sha256"]:
                    raise Refused("Journal belongs to another plan.")
                if event.get("bundle_id") not in plan["payload"]["targets"]:
                    raise Refused("Journal contains an unapproved app.")
                if event.get("event") == "uninstall_intent":
                    self.attempted.add(event["bundle_id"])

    def append(self, event, bid):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a") as handle:
            handle.write(json.dumps({"at": now(), "plan_sha256": self.plan["sha256"],
                                     "event": event, "bundle_id": bid}) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if event == "uninstall_intent":
            self.attempted.add(bid)


async def apply_plan(plan, approved_sha, device, journal_path, attempts=6, interval=2, progress=None, limit=None):
    if not isinstance(approved_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", approved_sha):
        raise Refused("Explicit approval of this plan's SHA-256 is required.")
    p = validate_plan(plan, approved_sha)
    require_device(p, device)
    if attempts < 2 or attempts > 30 or not 0 <= interval <= 10:
        raise Refused("Verification requires 2–30 attempts, with a 0–10 second interval.")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise Refused("Pilot limit must be a positive integer.")
    retained = sorted(b for b, d in p["decisions"].items() if d["action"] != "delete")
    if not retained:
        raise Refused("At least one retained app is required as a verification anchor.")
    guards = sorted({retained[0]} | {b for b, d in p["decisions"].items() if d["protected"]})
    removed, already_absent = [], []
    with device_lock(device.device_id):
        # Load only after acquiring the lock: a previous runner may have just
        # recorded an unresolved request while this runner was waiting.
        journal = Journal(journal_path, plan)
        initial = await device.read_apps()
        if not initial and p["inventory"]["apps"]:
            raise Refused("Empty device inventory cannot establish deletion success.")
        require_retained(p, initial)
        # All pending targets are checked before the first destructive request.
        for bid in p["targets"]:
            if bid in initial and (bid in journal.attempted or initial[bid] != p["inventory"]["apps"][bid]):
                raise Refused("Target changed or a previous attempt is unresolved; review a new plan: " + bid)
        for index, bid in enumerate(p["targets"], 1):
            if limit is not None and len(removed) >= limit:
                break
            live = await device.read_apps([bid] + guards)
            require_guards(guards, live)
            if bid not in live:
                if not await confirm_absent(device, bid, attempts, interval, guards, p):
                    raise Refused("App presence is inconsistent: " + bid)
                already_absent.append(bid)
                journal.append("absent_before_request", bid)
                continue
            if bid in journal.attempted or live[bid] != p["inventory"]["apps"][bid]:
                raise Refused("Target no longer matches the approved offloaded app: " + bid)
            journal.append("uninstall_intent", bid)  # Durable BEFORE requesting deletion.
            try:
                await device.uninstall(bid)
            except BaseException:
                journal.append("request_outcome_unknown", bid)
                raise  # Never blindly repeat a destructive request after a timeout/disconnect.
            if not await confirm_absent(device, bid, attempts, interval, guards, p):
                journal.append("absence_not_verified", bid)
                raise Refused("Uninstall returned but removal was not verified: " + bid)
            journal.append("verified_absent", bid)
            removed.append(bid)
            if progress:
                progress(index, len(p["targets"]))
        final = await device.read_apps()
        require_retained(p, final)
        reappeared = sorted(set(removed + already_absent) & set(final))
        if reappeared:
            raise Refused("Targets reappeared in final inventory: " + ", ".join(reappeared))
        # A pilot never establishes absence for targets it has not processed.
        # One final lookup omitting such a target cannot mark it complete.
        pending = sorted(set(p["targets"]) - set(removed + already_absent))
        if pending and limit is None:
            raise Refused("Targets remain in final inventory: " + ", ".join(pending))
        after = await device.free_bytes()
    before = p["inventory"].get("free_bytes")
    return {"plan_sha256": plan["sha256"], "completed_at": now(), "verified_removed_this_run": removed,
            "already_absent": already_absent, "pending": pending, "complete": not pending,
            "retained_apps_present": len(final),
            "free_bytes_before": before, "free_bytes_after": after,
            "observed_free_bytes_change": after - before if type(after) is int and type(before) is int else None,
            "note": "Storage changes include unrelated iOS activity; absence is metadata verification, not forensic erasure."}


async def verify_plan(plan, device):
    p = validate_plan(plan)
    require_device(p, device)
    first = await device.read_apps()
    await asyncio.sleep(2)
    second = await device.read_apps()
    require_retained(p, first)
    require_retained(p, second)
    if not first and p["inventory"]["apps"]:
        raise Refused("Empty inventory is insufficient verification.")
    return {"plan_sha256": plan["sha256"], "verified_at": now(),
            "absent_in_both_reads": sorted(set(p["targets"]) - set(first) - set(second)),
            "present_or_unstable": sorted(set(p["targets"]) & (set(first) | set(second))),
            "retained_apps_present": True, "free_bytes": await device.free_bytes()}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory", help="Read-only USB inventory; no automatic pairing")
    inv.add_argument("--device", required=True)
    inv.add_argument("--out", type=Path, required=True)
    plan = sub.add_parser("plan", help="Offline Delete/Keep/Review plan; never touches a phone")
    plan.add_argument("--inventory", type=Path, required=True)
    plan.add_argument("--decisions", type=Path, required=True)
    plan.add_argument("--out", type=Path, required=True)
    apply = sub.add_parser("apply", help="Destructive: only after user approval of this exact list")
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--approved-sha256", required=True)
    apply.add_argument("--journal", type=Path, required=True)
    apply.add_argument("--out", type=Path, required=True)
    apply.add_argument("--limit", type=int, help="Pilot: maximum new uninstall requests this run")
    verify = sub.add_parser("verify", help="Read-only independent verification")
    verify.add_argument("--plan", type=Path, required=True)
    verify.add_argument("--out", type=Path, required=True)
    return p


async def run(args):
    if args.command == "plan":
        plan = build_plan(read_json(args.inventory), read_json(args.decisions))
        write_json(args.out, plan)
        args.out.with_suffix(".md").write_text(render_plan(plan))
        return {"sha256": plan["sha256"], "delete_count": len(plan["payload"]["targets"]),
                "review_file": str(args.out.with_suffix(".md")), "awaiting_user_approval": True}
    if args.command == "inventory":
        async with PmdDevice(args.device) as device:
            data = {"schema": SCHEMA, "device_id": device.device_id, "observed_at": now(),
                    "apps": await device.read_apps(), "free_bytes": await device.free_bytes()}
        if not data["apps"]:
            raise Refused("Empty inventory; confirm device trust/access before proceeding.")
        write_json(args.out, data)
        return {"apps": len(data["apps"]), "offloaded": sum(a["state"] == "offloaded" for a in data["apps"].values()),
                "inventory_file": str(args.out)}
    plan = read_json(args.plan)
    p = validate_plan(plan, args.approved_sha256 if args.command == "apply" else None)
    last_progress = [time.monotonic()]
    def progress(done, total):
        if done == total or time.monotonic() - last_progress[0] >= 20:
            print(json.dumps({"verified": done, "total": total}), file=sys.stderr, flush=True)
            last_progress[0] = time.monotonic()
    async with PmdDevice(p["inventory"]["device_id"]) as device:
        if args.command == "apply":
            result = await apply_plan(plan, args.approved_sha256, device, args.journal, progress=progress, limit=args.limit)
        else:
            result = await verify_plan(plan, device)
    write_json(args.out, result)
    if args.command == "apply":
        return {"verified_removed_this_run": len(result["verified_removed_this_run"]),
                "already_absent": len(result["already_absent"]),
                "pending": len(result["pending"]), "complete": result["complete"],
                "free_bytes_after": result["free_bytes_after"], "result_file": str(args.out)}
    return {"verified_absent": len(result["absent_in_both_reads"]),
            "present_or_unstable": len(result["present_or_unstable"]), "result_file": str(args.out)}


def main():
    args = parser().parse_args()
    try:
        print(json.dumps(asyncio.run(run(args)), ensure_ascii=False))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({"stopped": True, "error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Conservative local Android review. No device changes outside approved apply.

An approval digest binds the reviewed list; a CLI flag cannot prove user consent.
Only run apply after the user has actually approved that exact rendered plan.
Uses Python 3.9+ standard library on Unix. No root, archive guesses, or data reset.
"""
import argparse
from collections import Counter
import contextlib
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata

SCHEMA = 1
PKG = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+")
HEX = re.compile(r"[0-9a-f]{64}")
ROLES = ("HOME", "DIALER", "SMS", "BROWSER")
SETTINGS = ("default_input_method", "enabled_accessibility_services", "always_on_vpn_app")
CATEGORIES = {"ordinary", "auth", "crypto", "password", "finance", "device-admin", "core", "unknown"}
SENSITIVE_IDS = {"io.metamask", "com.gemini.android.app", "org.toshi", "com.wallet.crypto.trustapp",
                 "app.phantom", "io.rabby", "com.x8bit.bitwarden", "com.agilebits.onepassword", "com.lastpass.lpandroid", "com.dashlane"}
TERMINAL = {"uninstall": "uninstall_absence_observed_twice", "clear_cache": "cache_request_accepted_unverified"}
HINT = re.compile(r"auth|crypto|wallet|password|passkey|bank|finance|payment|pay|vault|vpn|keyboard|launcher|device.?admin|mdm|enterprise|accessibility|account|bitwarden|lastpass|1password|dashlane|proton.?pass|otp|2fa|fido|coinbase|binance|robinhood|chase|wellsfargo|venmo|cashapp|shizuku|backup|firewall|security", re.I)
MAX_FILE = 4 * 1024 * 1024


class Refusal(Exception):
    """A deliberately non-sensitive, user-safe failure message."""


def require(ok, message="input or device evidence is invalid"):
    if not ok:
        raise Refusal(message)


def package(value):
    require(isinstance(value, str) and PKG.fullmatch(value), "package selection is invalid")
    return value


def user_id(value):
    require(re.fullmatch(r"0|[1-9][0-9]{0,5}", str(value)) is not None, "numeric user is required")
    return int(value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def seal(value):
    return dict(value, sha256=digest(value))


def unseal(value):
    require(isinstance(value, dict) and isinstance(value.get("sha256"), str), "saved evidence has no digest")
    body = {k: v for k, v in value.items() if k != "sha256"}
    require(value["sha256"] == digest(body), "saved evidence digest changed")
    return body


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON keys are not allowed")
        result[key] = value
    return result


def load(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "input must be a regular local file")
            raw = stream.read(MAX_FILE + 1)
        require(len(raw) <= MAX_FILE, "input file is too large")
        return json.loads(raw, object_pairs_hook=unique_object)
    except (OSError, ValueError, TypeError):
        raise Refusal("cannot read the JSON input") from None


def write_private(path, value, is_text=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not path.is_symlink(), "output must be a regular local file")
    raw = value if is_text else json.dumps(value, indent=2, ensure_ascii=True) + "\n"
    fd, name = tempfile.mkstemp(prefix=".android-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def execute(argv):
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, timeout=20, shell=False)
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        raise Refusal("device request timed out or disconnected; do not retry a mutation blindly") from None
    require(result.returncode == 0 and len(result.stdout) <= MAX_FILE and not result.stderr.strip(),
            "device request failed; no automatic retry")
    return result.stdout


def single(raw):
    value = raw.strip()
    require(value and len(value) <= 512 and not re.search(r"[\x00-\x1f\x7f]", value), "device identity is unavailable")
    return value


def inventory(raw, detail=True):
    result = {}
    for line in raw.splitlines():
        fields = line.split()
        require(fields and fields[0].startswith("package:"), "package inventory is unavailable")
        name = package(fields[0][8:])
        require(name not in result, "package inventory is ambiguous")
        item = {}
        for token in fields[1:]:
            match = re.fullmatch(r"(versionCode:|uid:|installer=)([^\s]+)", token)
            require(match is not None, "package inventory format is unsupported")
            key, value = match.groups()
            require(key not in item, "package inventory is ambiguous")
            if key == "installer=":
                item[key] = None if value == "null" else package(value)
            else:
                require(value.isdecimal() and len(value) <= 19 and int(value) <= 9223372036854775807, "package inventory is unavailable")
                item[key] = int(value)
        require(set(item) == ({"versionCode:", "uid:", "installer="} if detail else set()),
                "package inventory format is unsupported")
        result[name] = {"version": item.get("versionCode:"), "uid": item.get("uid:"), "installer": item.get("installer=")}
        require(len(result) <= 5000, "package inventory exceeds the supported bound")
    return result


def storage(raw):
    lines = raw.splitlines()
    if len(lines) != 2 or not re.search(r"(?:1K|1024)-blocks", lines[0]):
        return {"available_bytes": None, "total_bytes": None}
    parts = lines[1].split()
    if len(parts) != 6 or parts[-1] != "/data" or not all(x.isdecimal() for x in parts[1:4]):
        return {"available_bytes": None, "total_bytes": None}
    total, used, available = [int(x) * 1024 for x in parts[1:4]]
    if total <= 0 or min(used, available) < 0 or used + available > total:
        return {"available_bytes": None, "total_bytes": None}
    return {"available_bytes": available, "total_bytes": total}


def battery(raw):
    result = {"charge_percent": None, "temperature_c": None, "health_state": "unavailable",
              "remaining_capacity_percent": None, "cycle_count": None}
    if "Current Battery Service state:" not in raw or "UPDATES STOPPED" in raw:
        return result
    fields = dict(re.findall(r"^\s*(level|scale|temperature|health): (-?[0-9]+)\s*$", raw, re.M))
    if "level" in fields and "scale" in fields:
        level, scale = int(fields["level"]), int(fields["scale"])
        if 0 < scale <= 1000 and 0 <= level <= scale:
            result["charge_percent"] = round(100 * level / scale, 1)
    if "temperature" in fields and -1000 <= int(fields["temperature"]) <= 2000:
        result["temperature_c"] = int(fields["temperature"]) / 10
    result["health_state"] = {1: "unknown", 2: "good_enum_not_capacity", 3: "overheat", 4: "dead",
                              5: "over_voltage", 6: "unspecified_failure", 7: "cold"}.get(int(fields.get("health", "0")), "unavailable")
    return result


class Device:
    def __init__(self, serial, user, runner=execute, adb="adb"):
        require(isinstance(serial, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,179}", serial), "explicit device serial is required")
        self.serial, self.user, self.runner, self.adb = serial, user_id(user), runner, adb
        require(self.user == 0, "this preview supports only the Pixel owner user 0; profiles are guided")

    def call(self, *args):
        raw = self.runner([self.adb, "-s", self.serial] + list(args))
        require(isinstance(raw, str) and len(raw) <= MAX_FILE, "device response is unavailable")
        require(not re.search(r"permission deni(?:ed|al)|exception|unknown command|can't find service|error:", raw, re.I), "device capability is unavailable")
        return raw

    def shell(self, *args):
        return self.call("shell", *args)

    def anchor(self):
        require(self.call("get-state").strip() == "device", "selected device is not authorized and online")
        require(self.shell("am", "get-current-user").strip() == str(self.user), "foreground user changed or does not match")
        users = self.shell("pm", "list", "users")
        require(re.search(r"UserInfo\{" + str(self.user) + r":", users), "selected user is unavailable")
        aid = self.shell("settings", "--user", str(self.user), "get", "secure", "android_id").strip()
        require(re.fullmatch(r"[0-9a-fA-F]{1,16}", aid), "device binding is unavailable")
        props = {key: single(self.shell("getprop", prop)) for key, prop in (
            ("sdk", "ro.build.version.sdk"), ("model", "ro.product.model"),
            ("manufacturer", "ro.product.manufacturer"), ("build", "ro.build.fingerprint"))}
        require(props["sdk"].isdecimal() and 1 <= int(props["sdk"]) <= 1000, "Android version is unavailable")
        return dict(props, sdk=int(props["sdk"]), user=self.user, serial_hash=digest(self.serial),
                    device_hash=digest([self.serial, self.user, aid.lower()]))

    def packages(self):
        apps = inventory(self.shell("pm", "list", "packages", "-3", "-U", "-i", "--show-versioncode", "--user", str(self.user)))
        require(all(item["uid"] // 100000 == self.user for item in apps.values()), "inventory user binding is invalid")
        return apps

    def protections(self, extra):
        protected, missing = set(extra), []
        for role in ROLES:
            try:
                raw = self.shell("cmd", "role", "get-role-holders", "--user", str(self.user), "android.app.role." + role)
                protected.update(package(x) for x in raw.splitlines() if x)
            except Refusal:
                missing.append("role_" + role.lower())
        for setting in SETTINGS:
            try:
                raw = self.shell("settings", "--user", str(self.user), "get", "secure", setting).strip()
                require(bool(raw), "protection setting is unavailable")
                if raw != "null":
                    for component in raw.split(":"):
                        parts = component.split("/")
                        require(len(parts) == (1 if setting == "always_on_vpn_app" else 2), "protection setting format is unsupported")
                        require(len(parts) == 1 or re.fullmatch(r"[A-Za-z0-9_.$]+", parts[1]), "protection component is invalid")
                        protected.add(package(parts[0]))
            except Refusal:
                missing.append(setting)
        try:
            policy = self.shell("dumpsys", "device_policy")
            require("Current Device Policy Manager state:" in policy and
                    re.search(r"Enabled Device Admins \(User " + str(self.user) + r"[,)]", policy), "device-admin evidence is unavailable")
            protected.update(re.findall(r"([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+)/[A-Za-z0-9_.$]+", policy))
            if re.search(r"(?:device|profile)[\s_-]*owner\b", policy, re.I):
                missing.append("managed_device_or_profile_owner")
        except Refusal:
            missing.append("device_admins")
        return {"complete": not missing, "packages": sorted(protected), "unavailable": missing}

    def snapshot(self, extra=()):
        before = self.anchor()
        missing = []
        try:
            apps = self.packages()
            system = sorted(inventory(self.shell("pm", "list", "packages", "-s", "--user", str(self.user)), False))
        except Refusal:
            apps, system = {}, []
            missing.append("inventory")
        protection = self.protections(extra)
        uids = Counter(item["uid"] for item in apps.values())
        shared_or_core = {name for name, item in apps.items() if item["uid"] % 100000 < 10000 or uids[item["uid"]] > 1}
        protection["packages"] = sorted(set(protection["packages"]) | set(system) | shared_or_core)
        def optional(label, fn, fallback):
            try:
                return fn()
            except Refusal:
                missing.append(label)
                return fallback
        help_text = optional("cache_help", lambda: self.shell("pm", "help"), "")
        cache = bool(re.search(r"^\s*clear\s+\[--user USER_ID\]\s+\[--cache-only\]\s+PACKAGE\s*$", help_text, re.M))
        version_guard = bool(re.search(r"^\s*uninstall \[-k\] \[--user USER_ID\] \[--versionCode VERSION_CODE\]\s*$", help_text, re.M))
        facts = {key: optional(key, lambda p=prop: single(self.shell("getprop", p)), None) for key, prop in (
            ("security_patch", "ro.build.version.security_patch"), ("vendor_security_patch", "ro.vendor.build.security_patch"),
            ("verified_boot_reported", "ro.boot.verifiedbootstate"), ("flash_locked_reported", "ro.boot.flash.locked"))}
        disk = optional("storage", lambda: storage(self.shell("df", "-k", "/data")), storage(""))
        power = optional("battery", lambda: battery(self.shell("dumpsys", "battery")), battery(""))
        require(before == self.anchor(), "device identity or foreground user changed during collection")
        return seal({"schema": SCHEMA, "kind": "snapshot", "anchor": before, "packages": apps,
                     "system_packages": system, "protection": protection, "additional_protected": sorted(set(extra)),
                     "cache_only_advertised": cache, "uninstall_version_guard_advertised": version_guard, "storage": disk, "battery": power,
                     "observations": facts, "unavailable": missing})


def decision(value):
    require(isinstance(value, dict) and set(value) == {"package", "action", "category", "display_name", "reason"}, "decision fields are invalid")
    package(value["package"])
    require(value["action"] in {"keep", "clear_cache", "uninstall"} and value["category"] in CATEGORIES, "decision action or category is invalid")
    for key, bound in (("display_name", 120), ("reason", 500)):
        require(isinstance(value[key], str) and 0 < len(value[key]) <= bound and
                not re.search(r"[\x00-\x08\x0b-\x1f\x7f]", value[key]) and
                not any(unicodedata.category(c) == "Cf" for c in value[key]), "decision text is invalid")
    require(value["action"] == "keep" or (value["category"] == "ordinary" and value["package"] not in SENSITIVE_IDS and
            not HINT.search(value["package"] + " " + value["display_name"])),
            "sensitive, core, or unknown apps must be kept")
    return value


def eligible(snapshot, entry):
    decision(entry)
    if entry["action"] == "keep":
        return
    require(not snapshot["unavailable"] or "inventory" not in snapshot["unavailable"], "inventory is incomplete")
    require(snapshot["protection"]["complete"], "protection checks are incomplete; use guided Settings review")
    require(entry["package"] in snapshot["packages"] and entry["package"] not in snapshot["system_packages"] and
            entry["package"] not in snapshot["protection"]["packages"], "selected app is protected or not installed as a third-party app")
    if entry["action"] == "clear_cache":
        require(snapshot["anchor"]["sdk"] >= 33 and snapshot["cache_only_advertised"], "cache-only clearing is unsupported on this device")
    if entry["action"] == "uninstall":
        require(snapshot["uninstall_version_guard_advertised"], "version-guarded uninstall is unsupported on this device")


def make_plan(snapshot, decisions):
    unseal(snapshot)
    require(snapshot.get("kind") == "snapshot" and snapshot.get("schema") == SCHEMA, "snapshot format is unsupported")
    require(isinstance(decisions, list) and 0 < len(decisions) <= 200, "decisions must be a nonempty list")
    seen = set()
    for entry in decisions:
        eligible(snapshot, entry)
        require(entry["package"] not in seen, "duplicate package decisions are not allowed")
        seen.add(entry["package"])
    return seal({"schema": SCHEMA, "kind": "plan", "snapshot": snapshot, "decisions": decisions})


def checked_plan(plan):
    unseal(plan)
    require(plan.get("kind") == "plan" and plan.get("schema") == SCHEMA, "plan format is unsupported")
    require(make_plan(plan["snapshot"], plan["decisions"]) == plan, "plan no longer matches the reviewed evidence")
    return plan


def escaped(value):
    safe = html.escape(str(value), quote=True).replace("\n", "<br>").replace("\t", " ")
    return re.sub(r"[|`!\[\]()_*~\\]", lambda m: "&#{};".format(ord(m[0])), safe)


def markdown(value):
    if value["kind"] == "plan":
        anchor = value["snapshot"]["anchor"]
        rows = ["# Android cleanup review", "", "Review every row and the app identities with the user before apply.", "",
                "Target: user {} · {} · Android API {}".format(anchor["user"], escaped(anchor["model"]), anchor["sdk"]),
                "Build: " + escaped(anchor["build"]), "",
                "Uninstall deletes this user's app data. Cache requests do not prove bytes saved.", "",
                "| App | Package | Installed version | Action | Category | Reason |", "|---|---|---|---|---|---|"]
        rows += ["| " + " | ".join(escaped(x) for x in (e["display_name"], e["package"],
                 value["snapshot"]["packages"].get(e["package"], {}).get("version", "—"), e["action"], e["category"], e["reason"])) + " |" for e in value["decisions"]]
        rows += ["", "Approval SHA-256: `" + value["sha256"] + "`", "", "A digest argument binds this list; it does not itself establish user consent."]
        return "\n".join(rows) + "\n"
    return "# Android health observations\n\n| Observation | Result |\n|---|---|\n" + "\n".join(
        "| " + escaped(k) + " | " + escaped(v) + " |" for k, v in (
            ("Third-party app records (may be incomplete)", len(value["packages"])),
            ("Protection checks complete", value["protection"]["complete"]),
            ("Unavailable checks", ", ".join(value["unavailable"] + value["protection"]["unavailable"]) or "None reported"),
            ("Available storage bytes", value["storage"]["available_bytes"]),
            ("Battery charge percent (not capacity)", value["battery"]["charge_percent"]),
            ("Battery health enum (not remaining capacity)", value["battery"]["health_state"]),
            ("Remaining battery capacity / cycles", "Unavailable; use supported Pixel Settings"),
            ("Security patch reported", value["observations"]["security_patch"]),
            ("Verified Boot reported (not attestation)", value["observations"]["verified_boot_reported"]))) + "\n"


def save_report(path, value):
    write_private(path, value)
    if value["kind"] in {"snapshot", "plan"}:
        write_private(Path(path).with_suffix(".md"), markdown(value), True)


def assert_anchor(device, expected):
    require(device.anchor() == expected, "device binding, build, or foreground user no longer matches the plan")


def observed_target(device, expected, entry, version):
    """Two independent inventory reads, each bracketed by identity/user anchors."""
    observations = []
    for _ in range(2):
        assert_anchor(device, expected)
        apps = device.packages()
        assert_anchor(device, expected)
        observations.append(apps.get(entry["package"]))
    if entry["action"] == "uninstall":
        return all(item is None for item in observations)
    return all(item is not None and item["version"] == version for item in observations)


@contextlib.contextmanager
def device_lock(directory, serial_hash):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not directory.is_symlink() and directory.stat().st_uid == os.getuid() and
            directory.stat().st_mode & 0o077 == 0, "state directory must be private and owned by you")
    fd = os.open(directory / (serial_hash + ".lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "device lock must be a regular local file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal("another cleanup is active for this device") from None
        yield directory / (serial_hash + ".jsonl")
    finally:
        os.close(fd)


class Journal:
    def __init__(self, path, binding):
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        self.events = []
        try:
            require(stat.S_ISREG(os.fstat(self.fd).st_mode) and os.fstat(self.fd).st_mode & 0o077 == 0,
                    "journal must be a private regular local file")
            with os.fdopen(os.dup(self.fd), "r", encoding="utf-8") as stream:
                raw = stream.read(MAX_FILE + 1)
            require(len(raw) <= MAX_FILE, "journal is too large")
            if raw:
                require(raw.endswith("\n"), "journal has an unfinished record; do not retry")
                records = [json.loads(x, object_pairs_hook=unique_object) for x in raw.splitlines()]
                require(records[0] == {"kind": "binding", **binding}, "journal belongs to another device or user")
                self.events = records[1:]
                for e in self.events:
                    require(isinstance(e, dict) and set(e) == {"plan", "device", "user", "package", "action", "phase", "status"} and
                            HEX.fullmatch(e["plan"]) and HEX.fullmatch(e["device"]) and e["action"] in {"clear_cache", "uninstall"} and
                            e["phase"] in {"intent", "result"}, "journal record is invalid")
                    package(e["package"])
                    user_id(e["user"])
            else:
                self.append({"kind": "binding", **binding}, remember=False)
                directory = os.open(Path(path).parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        except Exception:
            os.close(self.fd)
            raise

    def append(self, event, remember=True):
        raw = (json.dumps(event, sort_keys=True) + "\n").encode()
        require(os.write(self.fd, raw) == len(raw), "journal could not be written; do not retry")
        os.fsync(self.fd)
        if remember:
            self.events.append(event)

    def close(self):
        os.close(self.fd)


def apply_plan(device, plan, approved, journal_path, state_dir, limit=2, continue_after_pilot=False):
    checked_plan(plan)
    require(approved == plan["sha256"], "approval digest does not match the exact reviewed plan")
    require(type(limit) is int and 1 <= limit <= 2, "pilot limit must be one or two apps")
    baseline = plan["snapshot"]
    expected = baseline["anchor"]
    require(device.user == expected["user"] and digest(device.serial) == expected["serial_hash"], "explicit device and user do not match the plan")
    targets = [e for e in plan["decisions"] if e["action"] != "keep"]
    result = {"schema": SCHEMA, "kind": "apply_result", "plan_sha256": plan["sha256"], "outcomes": [],
              "unprocessed": [e["package"] for e in targets], "storage_plan_baseline": baseline["storage"], "storage_before": storage(""), "storage_after": storage(""),
              "note": "Request status is separate from observed removal. Cache contents and per-app savings are unverified."}
    with device_lock(state_dir, expected["serial_hash"]) as ledger_path:
        journals = []
        try:
            journals.append(Journal(ledger_path, {"serial_hash": expected["serial_hash"]}))
            require(Path(journal_path).resolve() != Path(ledger_path).resolve(), "audit journal must differ from the internal ledger")
            journals.append(Journal(journal_path, {"device": expected["device_hash"], "user": expected["user"]}))
            all_events = [e for journal in journals for e in journal.events]
            event_key = lambda e: (e["plan"], e["device"], e["user"], e["package"], e["action"])
            pending = {event_key(e) for e in all_events if e["phase"] == "intent"} - {
                event_key(e) for e in all_events if e["phase"] == "result" and e["status"] == TERMINAL[e["action"]]}
            previous = [e for e in all_events if e["plan"] == plan["sha256"]]
            attempted = {e["package"] for e in previous if e["phase"] == "intent"}
            pilot = min(2, len(targets))
            if continue_after_pilot:
                require(len(attempted) >= pilot and all(e["action"] == "uninstall" for e in targets),
                        "continuation needs a completed uninstall-only pilot; cache and mixed plans need guided review and a new plan")
                for entry in targets[:pilot]:
                    reports = {e["status"] for e in previous if e["package"] == entry["package"] and e["phase"] == "result"}
                    require(reports == {"uninstall_absence_observed_twice"}, "pilot has no verified removal evidence")
                    require(observed_target(device, expected, entry, baseline["packages"][entry["package"]]["version"]),
                            "pilot removal no longer verifies; review a fresh plan")
                slots = limit
            else:
                slots = max(0, min(limit, pilot - len(attempted)))
            measured = False
            for entry in targets:
                name = entry["package"]
                if name in attempted:
                    reports = {e["status"] for e in previous if e["package"] == name and e["phase"] == "result"}
                    require(len(reports) <= 1, "journal has conflicting outcomes; review before continuing")
                    status = next(iter(reports), "pending_request_do_not_retry")
                    result["outcomes"].append({"package": name, "status": status, "prior_attempt": True})
                    result["unprocessed"].remove(name)
                    if status not in {"uninstall_absence_observed_twice", "cache_request_accepted_unverified"}:
                        break
                    continue
                if slots == 0:
                    continue
                if any(key[1:4] == (expected["device_hash"], expected["user"], name) for key in pending):
                    result["outcomes"].append({"package": name, "status": "prior_pending_request_do_not_retry"})
                    break
                status = "preflight_blocked"
                sent = False
                def record(phase, state):
                    event = {"plan": plan["sha256"], "device": expected["device_hash"], "user": expected["user"],
                             "package": name, "action": entry["action"], "phase": phase, "status": state}
                    for journal in journals:
                        journal.append(event)
                try:
                    fresh = device.snapshot(baseline["additional_protected"])
                    require(fresh["anchor"] == expected, "device baseline changed")
                    eligible(fresh, entry)
                    require(fresh["packages"][name] == baseline["packages"][name], "selected app changed; a fresh review is required")
                    if not measured:
                        result["storage_before"], measured = fresh["storage"], True
                    record("intent", "pending_request_do_not_retry")
                    sent = True
                    slots -= 1
                    if entry["action"] == "clear_cache":
                        reply = device.shell("pm", "clear", "--user", str(device.user), "--cache-only", package(name))
                    else:
                        version = str(baseline["packages"][name]["version"])
                        require(version.isdecimal() and len(version) <= 19, "version guard is invalid")
                        reply = device.shell("pm", "uninstall", "--user", str(device.user), "--versionCode", version, package(name))
                    require(reply.strip() == "Success", "device did not report success; do not retry")
                    ok = observed_target(device, expected, entry, baseline["packages"][name]["version"])
                    status = ("uninstall_absence_observed_twice" if entry["action"] == "uninstall" else "cache_request_accepted_unverified") if ok else "request_reported_success_verification_failed"
                    record("result", status)
                    require(ok, "target state did not match the request")
                except (Refusal, OSError):
                    if sent and status == "preflight_blocked":
                        status = "pending_request_do_not_retry"
                    result["outcomes"].append({"package": name, "status": status})
                    if sent:
                        result["unprocessed"].remove(name)
                    break
                result["outcomes"].append({"package": name, "status": status})
                result["unprocessed"].remove(name)
            try:
                assert_anchor(device, expected)
                result["storage_after"] = storage(device.shell("df", "-k", "/data"))
                assert_anchor(device, expected)
            except Refusal:
                pass
        finally:
            for journal in journals:
                journal.close()
    return seal(result)


def verify_plan(device, plan):
    checked_plan(plan)
    expected = plan["snapshot"]["anchor"]
    assert_anchor(device, expected)
    outcomes = []
    for entry in plan["decisions"]:
        if entry["action"] != "keep":
            ok = observed_target(device, expected, entry, plan["snapshot"]["packages"][entry["package"]]["version"])
            outcomes.append({"package": entry["package"], "expected_state_observed_twice": ok,
                             "claim": "absence_observed_not_attributed" if entry["action"] == "uninstall" else "package_retention_only_cache_contents_unverified"})
    disk = storage(device.shell("df", "-k", "/data"))
    assert_anchor(device, expected)
    return seal({"schema": SCHEMA, "kind": "verification", "plan_sha256": plan["sha256"], "outcomes": outcomes,
                 "storage_observed": disk, "note": "Storage is device-wide; no exact per-app cache savings are claimed."})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("snapshot", "plan", "apply", "verify"):
        p = sub.add_parser(command)
        p.add_argument("--out", required=True)
        if command != "plan":
            p.add_argument("--serial", required=True)
            p.add_argument("--user", required=True)
        if command == "snapshot":
            p.add_argument("--protect", action="append", default=[])
        if command == "plan":
            p.add_argument("--snapshot", required=True)
            p.add_argument("--decisions", required=True)
        if command in {"apply", "verify"}:
            p.add_argument("--plan", required=True)
        if command == "apply":
            p.add_argument("--approved-sha256", required=True, help="Only after actual user approval of the exact rendered plan; the flag is not consent")
            p.add_argument("--journal", required=True)
            p.add_argument("--limit", type=int, default=2)
            p.add_argument("--continue-after-pilot", action="store_true", help="At most two more uninstall requests after independently rechecking the completed uninstall-only pilot")
            p.add_argument("--state-dir", default=str(Path.home() / ".local" / "state" / "android-health-cleanup"),
                           help="Persistent private replay ledger; do not replace, clear, or switch this directory to resume")
    args = parser.parse_args(argv)
    try:
        require(Path(args.out).suffix.lower() == ".json", "output must use the .json extension")
        inputs = [getattr(args, name, None) for name in ("plan", "snapshot", "decisions", "journal")]
        output_paths = {Path(args.out).resolve(), Path(args.out).with_suffix(".md").resolve()}
        require(not any(Path(path).resolve() in output_paths for path in inputs if path), "outputs must differ from input and journal files")
        if args.command == "plan":
            value = make_plan(load(args.snapshot), load(args.decisions))
        else:
            device = Device(args.serial, args.user)
            if args.command == "snapshot":
                value = device.snapshot([package(x) for x in args.protect])
            elif args.command == "apply":
                value = apply_plan(device, load(args.plan), args.approved_sha256, args.journal, args.state_dir, args.limit, args.continue_after_pilot)
            else:
                value = verify_plan(device, load(args.plan))
        save_report(args.out, value)
        count = len(value.get("packages", value.get("decisions", value.get("outcomes", []))))
        print("Saved {} records to {}".format(count, json.dumps(args.out)))
        if value["kind"] == "apply_result" and any(e["status"] not in TERMINAL.values() for e in value["outcomes"]):
            return 3
        if value["kind"] == "verification" and any(not e["expected_state_observed_twice"] for e in value["outcomes"]):
            return 3
        return 0
    except (Refusal, OSError, KeyError, TypeError, ValueError, RecursionError):
        print("Stopped: invalid, changed, unavailable, or unsafe evidence. Review the local plan and journal; do not blindly retry device changes.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

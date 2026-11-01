#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded, read-only iPhone snapshot; offline, evidence-limited scorecard.

No cache/file deletion, profile changes, backup, log capture or firmware actions.
"""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import sys
from datetime import datetime
from pathlib import Path

from cleanup import PMD_VERSION, Refused, device_lock, now, read_json, write_json

IDENTITY_KEYS = ("ProductType", "ProductVersion", "BuildVersion")
STORAGE_KEYS = ("TotalDataCapacity", "TotalDataAvailable")
CHARGE_KEYS = ("BatteryCurrentCapacity", "BatteryIsCharging", "BatteryIsFullyCharged")
# Preserve exact field names; capacity/temperature units vary across devices.
# Never derive an Apple Battery Health percentage from these raw counters.
BATTERY_KEYS = ("CycleCount", "DesignCapacity", "NominalChargeCapacity",
                "MaximumCapacityPercent", "CurrentCapacity", "MaxCapacity",
                "Temperature", "Voltage", "IsCharging")


def select_scalars(raw, keys):
    if not isinstance(raw, dict):
        return {}
    return {key: value for key in keys if key in raw
            for value in [raw[key]]
            if type(value) in (int, float, bool, str)
            and (not isinstance(value, str) or len(value) <= 80)
            and (not isinstance(value, float) or math.isfinite(value))
            and (type(value) is not int or abs(value) <= 10**18)}


class ReadOnlyDevice:
    def __init__(self, device_id, timeout=20):
        self.device_id, self.timeout = device_id, timeout
        self.lockdown = self.diagnostics = None

    async def __aenter__(self):
        if importlib.metadata.version("pymobiledevice3") != PMD_VERSION:
            raise Refused("Use the reviewed pymobiledevice3==" + PMD_VERSION + " environment.")
        from pymobiledevice3.lockdown import create_using_usbmux
        try:
            self.lockdown = await asyncio.wait_for(create_using_usbmux(
                serial=self.device_id, connection_type="USB", autopair=False), self.timeout)
            if not self.lockdown.paired or self.lockdown.udid != self.device_id:
                raise Refused("Select the already-trusted USB device; no automatic pairing.")
            return self
        except BaseException:
            await self.__aexit__(None, None, None)
            raise

    async def __aexit__(self, *args):
        for obj in (self.diagnostics, self.lockdown):
            if obj is not None:
                try:
                    await asyncio.wait_for(obj.close(), 5)
                except Exception:
                    pass

    async def identity(self):
        data = {}
        for key in IDENTITY_KEYS:
            data[key] = await asyncio.wait_for(self.lockdown.get_value(key=key), self.timeout)
        return data

    async def storage(self):
        return await asyncio.wait_for(self.lockdown.get_value(
            domain="com.apple.disk_usage"), self.timeout)

    async def charge(self):
        return await asyncio.wait_for(self.lockdown.get_value(
            domain="com.apple.mobile.battery"), self.timeout)

    async def battery(self):
        from pymobiledevice3.services.diagnostics import DiagnosticsService
        self.diagnostics = DiagnosticsService(self.lockdown)
        await asyncio.wait_for(self.diagnostics.__aenter__(), self.timeout)
        return await asyncio.wait_for(self.diagnostics.get_battery(), self.timeout)


async def collect(device):
    result = {"schema": 1, "kind": "iphone-health-snapshot",
              "device_id": device.device_id, "observed_at": now(), "sections": {}}
    # A single collector serializes service calls; agents analyze this file offline.
    for name, reader, keys in (
        ("identity", device.identity, IDENTITY_KEYS),
        ("storage", device.storage, STORAGE_KEYS),
        ("charge", device.charge, CHARGE_KEYS),
        ("battery_raw", device.battery, BATTERY_KEYS),
    ):
        try:
            values = select_scalars(await asyncio.wait_for(reader(), 65), keys)
            result["sections"][name] = {"status": "observed" if values else "unavailable",
                                         "values": values}
        except Exception as exc:
            # Do not serialize full service errors (which can contain private payloads).
            # Library disconnects do not all inherit builtin ConnectionError. Stop
            # after any failure, without probing more services on a broken session.
            result["sections"][name] = {"status": "unavailable", "values": {},
                                         "reason": type(exc).__name__}
            break
    result["finished_at"] = now()
    return result


def valid_number(value):
    return type(value) in (int, float) and 0 <= value <= 10**18 and math.isfinite(value)


def scorecard(snapshot):
    if snapshot.get("schema") != 1 or snapshot.get("kind") != "iphone-health-snapshot":
        raise Refused("Not an iPhone health snapshot.")
    device_id, observed_at = snapshot.get("device_id"), snapshot.get("observed_at")
    if not isinstance(device_id, str) or not device_id.strip() or len(device_id) > 256:
        raise Refused("Snapshot lacks exact-device provenance.")
    try:
        timestamp = datetime.fromisoformat(observed_at)
        if timestamp.utcoffset() is None:
            raise ValueError("Missing timezone")
    except (TypeError, ValueError):
        raise Refused("Snapshot lacks a valid timezone-aware observation timestamp.")
    sections = snapshot.get("sections")
    if not isinstance(sections, dict):
        raise Refused("Snapshot sections are missing.")
    if any(not isinstance(s, dict) or not isinstance(s.get("values"), dict)
           or s.get("status") not in ("observed", "unavailable") for s in sections.values()):
        raise Refused("Malformed snapshot section.")
    sources = {"identity": "lockdown ProductType/ProductVersion/BuildVersion",
               "storage": "lockdown com.apple.disk_usage",
               "charge": "lockdown com.apple.mobile.battery",
               "battery_raw": "diagnostics relay IOPMPowerSource; units unnormalized"}
    coverage = [{"section": key, "status": sections.get(key, {}).get("status", "not_attempted"),
                 "fields": sorted(select_scalars(sections.get(key, {}).get("values", {}), allowed))}
                for key, allowed in (("identity", IDENTITY_KEYS), ("storage", STORAGE_KEYS),
                                     ("charge", CHARGE_KEYS), ("battery_raw", BATTERY_KEYS))]
    storage = sections.get("storage", {})
    values = storage.get("values", {}) if storage.get("status") == "observed" else {}
    free, total = values.get("TotalDataAvailable"), values.get("TotalDataCapacity")
    valid_storage = valid_number(free) and valid_number(total) and total > 0 and free <= total
    return {"schema": 1, "kind": "iphone-health-scorecard", "snapshot_at": timestamp.isoformat(),
            "device_id": device_id,
            "device_reference": hashlib.sha256(device_id.encode()).hexdigest()[:12],
            "sources": sources, "coverage": coverage,
            "overall_score": None, "performance_improvement_verified": False,
            "checks": [
                {"area": "Storage", "status": ("attention" if free < 1_000_000_000 else "observed")
                 if valid_storage else "unknown",
                 "free_bytes": free if valid_storage else None,
                 "total_bytes": total if valid_storage else None,
                 "next": "Review iPhone Storage recommendations and exact cleanup candidates."
                 if valid_storage else "Check Settings > General > iPhone Storage."},
                {"area": "Battery health", "status": "unknown",
                 "next": "Read Battery Health and any service/peak-performance message in Settings; raw counters are not a diagnosis."},
                {"area": "Performance and usage", "status": "unknown",
                 "next": "Record the slow task, power mode, temperature, network and Battery usage time window; request selected logs only if needed."},
                {"area": "Security posture", "status": "unknown",
                 "next": "Compare observed iOS/build with current Apple advisories for this model; review update settings and management profiles."},
            ], "limits": ["No numeric health or security certification is calculated.",
                           "Unavailable data is unknown, not a passing check.",
                           "Snapshot excludes browsing history, messages, photos, logs and backups."]}


def render(card):
    lines = ["# iPhone health: preliminary evidence", "",
             "This snapshot is partial. This report command makes no device changes; action approvals are tracked separately.", "",
             "Device reference: {}. Observed: {}.".format(card["device_reference"], card["snapshot_at"]),
             "Exact device identity and source details are in the private JSON scorecard.", "",
             "Coverage: " + "; ".join(item["section"] + "=" + item["status"] for item in card["coverage"]),
             "Storage source: lockdown com.apple.disk_usage. Other health areas need follow-up evidence.", "",
             "| Area | Status | Next step |", "|---|---|---|"]
    for row in card["checks"]:
        detail = row["next"]
        if row["area"] == "Storage" and row["free_bytes"] is not None:
            detail = "{:.2f} GB free (decimal). ".format(row["free_bytes"] / 1e9) + detail
        lines.append("| {} | {} | {} |".format(row["area"], row["status"], detail))
    lines += ["", "No overall score: battery, usage and security need additional evidence.",
              "Free space changes do not prove a faster phone.", ""]
    return "\n".join(lines)


async def run(args):
    if args.out.suffix.lower() != ".json":
        raise Refused("Use a .json output path; the report also creates a separate .md file.")
    if args.command == "snapshot":
        with device_lock(args.device):
            async with ReadOnlyDevice(args.device) as device:
                data = await collect(device)
        write_json(args.out, data)
        return {"snapshot_file": str(args.out), "observed_sections": sum(
            s["status"] == "observed" for s in data["sections"].values()), "device_changes": 0}
    review = args.out.with_suffix(".md")
    paths = (args.snapshot.resolve(), args.out.resolve(), review.resolve())
    if len(set(paths)) != 3:
        raise Refused("Input snapshot and JSON/Markdown outputs must be different files.")
    data = scorecard(read_json(args.snapshot))
    data["input_snapshot"] = str(args.snapshot.resolve())
    write_json(args.out, data)
    # The rendered report only contains fixed text and validated numeric storage values.
    review.write_text(render(data))
    review.chmod(0o600)
    return {"scorecard_file": str(args.out), "review_file": str(review), "device_changes": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot", help="Read a trusted USB iPhone; no writes to the phone")
    snapshot.add_argument("--device", required=True)
    snapshot.add_argument("--out", type=Path, required=True)
    report = commands.add_parser("report", help="Create an offline preliminary scorecard")
    report.add_argument("--snapshot", type=Path, required=True)
    report.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(run(args))))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({"stopped": True, "error": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline diagnostic boundaries; no live iPhone is contacted."""
import asyncio
import copy
import importlib.util
import inspect
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("iphone_health", SCRIPTS / "health.py")
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
sys.path.remove(str(SCRIPTS))


class FakeReadOnly:
    device_id = "test-phone"

    def __init__(self):
        self.calls = []

    async def identity(self):
        self.calls.append("identity")
        return {"ProductType": "test-model", "ProductVersion": "test-version",
                "BuildVersion": "test-build", "SerialNumber": "must-not-save"}

    async def storage(self):
        self.calls.append("storage")
        return {"TotalDataCapacity": 64_000_000_000, "TotalDataAvailable": 500_000_000}

    async def charge(self):
        self.calls.append("charge")
        return {"BatteryCurrentCapacity": 100, "BatteryIsCharging": True}

    async def battery(self):
        self.calls.append("battery")
        return {"CycleCount": 300, "Temperature": 2931, "Serial": "private",
                "BatteryData": {"SerialNumber": "private"}}


class SnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_single_collector_allowlists_fields_and_calls_only_reads(self):
        phone = FakeReadOnly()
        snapshot = await h.collect(phone)
        self.assertEqual(phone.calls, ["identity", "storage", "charge", "battery"])
        self.assertNotIn("must-not-save", str(snapshot))
        self.assertNotIn("private", str(snapshot))
        self.assertEqual(snapshot["sections"]["battery_raw"]["values"],
                         {"CycleCount": 300, "Temperature": 2931})

    async def test_missing_battery_remains_unavailable(self):
        phone = FakeReadOnly()
        phone.battery = mock.AsyncMock(return_value=None)
        snapshot = await h.collect(phone)
        self.assertEqual(snapshot["sections"]["battery_raw"]["status"], "unavailable")
        self.assertEqual(h.scorecard(snapshot)["checks"][1]["status"], "unknown")

    async def test_transport_failure_stops_further_reads(self):
        phone = FakeReadOnly()
        phone.storage = mock.AsyncMock(side_effect=ConnectionError("secret payload"))
        result = await h.collect(phone)
        self.assertEqual(phone.calls, ["identity"])
        self.assertNotIn("secret payload", str(result))
        self.assertNotIn("charge", result["sections"])

    async def test_raw_full_charge_never_becomes_battery_health(self):
        result = h.scorecard(await h.collect(FakeReadOnly()))
        self.assertIsNone(result["overall_score"])
        self.assertEqual(result["checks"][1]["status"], "unknown")
        self.assertFalse(result["performance_improvement_verified"])

    async def test_invalid_and_conflicting_storage_cannot_pass(self):
        base = await h.collect(FakeReadOnly())
        for free, total in [(True, 200), (-1, 200), (201, 200), (1, 0), (float("nan"), 200), ("10", 200)]:
            data = copy.deepcopy(base)
            data["sections"]["storage"]["values"] = {
                "TotalDataCapacity": total, "TotalDataAvailable": free}
            self.assertEqual(h.scorecard(data)["checks"][0]["status"], "unknown")

    async def test_unknown_security_does_not_pass_for_new_looking_version(self):
        result = h.scorecard(await h.collect(FakeReadOnly()))
        self.assertEqual(result["checks"][3]["status"], "unknown")

    async def test_no_device_data_rendered_as_markup(self):
        data = await h.collect(FakeReadOnly())
        data["sections"]["identity"]["values"]["ProductType"] = '<img src="https://test.invalid">'
        data["sections"]["battery_raw"]["values"]["CycleCount"] = '[x](https://test.invalid)'
        rendered = h.render(h.scorecard(data))
        self.assertNotIn("test.invalid", rendered)


class StructureTests(unittest.TestCase):
    def test_allowlist_rejects_nested_large_and_nonfinite_values(self):
        self.assertEqual(h.select_scalars({"a": {}, "b": "x" * 81, "c": float("inf"), "d": 2},
                                         ("a", "b", "c", "d")), {"d": 2})

    def test_rejects_other_snapshot_types(self):
        with self.assertRaises(h.Refused):
            h.scorecard({"schema": 1, "kind": "anything-else"})

    def test_pinned_library_diagnostic_contract(self):
        try:
            from pymobiledevice3.services.diagnostics import DiagnosticsService
            from pymobiledevice3.lockdown import create_using_usbmux
        except ModuleNotFoundError:
            self.skipTest("Run in the pinned environment for the API contract check")
        self.assertTrue(inspect.iscoroutinefunction(DiagnosticsService.get_battery))
        self.assertIn("autopair", inspect.signature(create_using_usbmux).parameters)
        self.assertIn("connection_type", inspect.signature(create_using_usbmux).parameters)
        self.assertEqual(h.importlib.metadata.version("pymobiledevice3"), h.PMD_VERSION)


if __name__ == "__main__":
    unittest.main()

# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline adapter and artifact safety checks; never contact a phone."""
import copy
import importlib
import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("iphone_health_safety", SCRIPTS / "health.py")
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
sys.path.remove(str(SCRIPTS))

DEVICE_ID = "00008110-001234567890801E"


def snapshot():
    return {
        "schema": 1, "kind": "iphone-health-snapshot", "device_id": DEVICE_ID,
        "observed_at": "2026-10-31T12:34:56+00:00",
        "sections": {
            "identity": {"status": "observed", "values": {
                "ProductType": "iPhone-test", "ProductVersion": "test-version",
                "BuildVersion": "test-build"}},
            "storage": {"status": "observed", "values": {
                "TotalDataAvailable": 5_000_000_000,
                "TotalDataCapacity": 64_000_000_000}},
        },
    }


class AdapterSafetyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        try:
            self.lockdown_module = importlib.import_module("pymobiledevice3.lockdown")
        except ModuleNotFoundError:
            self.skipTest("Pinned environment required for adapter contract checks")

    def client(self, paired=True, udid=DEVICE_ID):
        return SimpleNamespace(paired=paired, udid=udid,
                               close=mock.AsyncMock(), get_value=mock.AsyncMock())

    async def test_factory_uses_exact_usb_device_without_pairing_and_closes(self):
        client = self.client()
        factory = mock.AsyncMock(return_value=client)
        with mock.patch.object(self.lockdown_module, "create_using_usbmux", factory), \
                mock.patch.object(h.importlib.metadata, "version", return_value=h.PMD_VERSION):
            async with h.ReadOnlyDevice(DEVICE_ID) as adapter:
                self.assertIs(adapter.lockdown, client)
                factory.assert_awaited_once_with(
                    serial=DEVICE_ID, connection_type="USB", autopair=False)
                client.close.assert_not_awaited()
        client.close.assert_awaited_once_with()
        client.get_value.assert_not_awaited()

    async def test_unpaired_and_wrong_device_refused_and_closed_without_reads(self):
        for paired, udid in [(False, DEVICE_ID), (True, "00008110-OTHER-DEVICE")]:
            with self.subTest(paired=paired, udid=udid):
                client = self.client(paired=paired, udid=udid)
                factory = mock.AsyncMock(return_value=client)
                with mock.patch.object(self.lockdown_module, "create_using_usbmux", factory), \
                        mock.patch.object(h.importlib.metadata, "version", return_value=h.PMD_VERSION):
                    with self.assertRaises(h.Refused):
                        async with h.ReadOnlyDevice(DEVICE_ID):
                            self.fail("Untrusted or wrong device entered adapter context")
                client.close.assert_awaited_once_with()
                client.get_value.assert_not_awaited()

    async def test_version_mismatch_refuses_before_factory_call(self):
        factory = mock.AsyncMock()
        with mock.patch.object(self.lockdown_module, "create_using_usbmux", factory), \
                mock.patch.object(h.importlib.metadata, "version", return_value="unreviewed-version"):
            with self.assertRaises(h.Refused):
                async with h.ReadOnlyDevice(DEVICE_ID):
                    self.fail("Unreviewed dependency entered adapter context")
        factory.assert_not_called()

    async def test_normal_context_exit_closes_both_services_after_body_error(self):
        client = self.client()
        diagnostics = SimpleNamespace(close=mock.AsyncMock())
        with mock.patch.object(self.lockdown_module, "create_using_usbmux", mock.AsyncMock(return_value=client)), \
                mock.patch.object(h.importlib.metadata, "version", return_value=h.PMD_VERSION):
            with self.assertRaisesRegex(ValueError, "offline body failure"):
                async with h.ReadOnlyDevice(DEVICE_ID) as adapter:
                    adapter.diagnostics = diagnostics
                    raise ValueError("offline body failure")
        diagnostics.close.assert_awaited_once_with()
        client.close.assert_awaited_once_with()


class CollectorSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_cleanup_lock_prevents_snapshot_opening_device(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "snapshot.json"
            args = SimpleNamespace(command="snapshot", device=DEVICE_ID, out=out)
            with h.device_lock(DEVICE_ID), mock.patch.object(h, "ReadOnlyDevice") as adapter:
                with self.assertRaises(h.Refused):
                    await h.run(args)
                adapter.assert_not_called()
            self.assertFalse(out.exists())

    async def test_pinned_disconnect_stops_remaining_readers(self):
        try:
            from pymobiledevice3.exceptions import ConnectionTerminatedError
        except ModuleNotFoundError:
            self.skipTest("Pinned environment required for real disconnect class")
        phone = SimpleNamespace(
            device_id=DEVICE_ID,
            identity=mock.AsyncMock(return_value={"ProductType": "iPhone-test"}),
            storage=mock.AsyncMock(side_effect=ConnectionTerminatedError("private payload")),
            charge=mock.AsyncMock(return_value={"BatteryCurrentCapacity": 80}),
            battery=mock.AsyncMock(return_value={"CycleCount": 20}),
        )
        result = await h.collect(phone)
        phone.storage.assert_awaited_once_with()
        phone.charge.assert_not_awaited()
        phone.battery.assert_not_awaited()
        self.assertEqual(result["sections"]["identity"]["status"], "observed")
        self.assertEqual(result["sections"]["storage"]["status"], "unavailable")
        self.assertNotIn("private payload", json.dumps(result))


class ReportSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_report_writes_distinct_private_parseable_files_without_device_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, out = root / "snapshot.json", root / "report.json"
            source.write_text(json.dumps(snapshot()))
            original = source.read_bytes()
            with mock.patch.object(h, "ReadOnlyDevice") as adapter:
                result = await h.run(SimpleNamespace(command="report", snapshot=source, out=out))
                adapter.assert_not_called()
            review = Path(result["review_file"])
            self.assertEqual(Path(result["scorecard_file"]), out)
            self.assertNotEqual(out.resolve(), review.resolve())
            self.assertNotEqual(source.resolve(), review.resolve())
            self.assertEqual(json.loads(out.read_text())["kind"], "iphone-health-scorecard")
            self.assertIn("|", review.read_text())
            self.assertEqual(source.read_bytes(), original)
            for path in (out, review):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    async def test_markdown_output_suffix_refused_without_creating_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, out = root / "snapshot.json", root / "report.md"
            source.write_text(json.dumps(snapshot()))
            with self.assertRaises(h.Refused):
                await h.run(SimpleNamespace(command="report", snapshot=source, out=out))
            self.assertFalse(out.exists())

    async def test_input_cannot_be_overwritten_by_json_or_derived_markdown(self):
        for source_name, out_name in [("report.json", "report.json"),
                                      ("report.md", "report.json")]:
            with self.subTest(source=source_name, output=out_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source, out = root / source_name, root / out_name
                source.write_text(json.dumps(snapshot()))
                original = source.read_bytes()
                with self.assertRaises(h.Refused):
                    await h.run(SimpleNamespace(command="report", snapshot=source, out=out))
                self.assertEqual(source.read_bytes(), original)
                if out != source:
                    self.assertFalse(out.exists())

    async def test_symlink_alias_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, out = root / "snapshot.json", root / "alias.json"
            source.write_text(json.dumps(snapshot()))
            original = source.read_bytes()
            out.symlink_to(source)
            with self.assertRaises(h.Refused):
                await h.run(SimpleNamespace(command="report", snapshot=source, out=out))
            self.assertTrue(out.is_symlink())
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(out.with_suffix(".md").exists())

    async def test_missing_or_invalid_provenance_refused(self):
        invalid = [
            ("device_id", None), ("device_id", ""),
            ("observed_at", None), ("observed_at", "not-a-date"),
            ("observed_at", "2026-10-31T12:34:56"),
        ]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(snapshot())
                if value is None:
                    data.pop(key)
                else:
                    data[key] = value
                with self.assertRaises(h.Refused):
                    h.scorecard(data)


if __name__ == "__main__":
    unittest.main()

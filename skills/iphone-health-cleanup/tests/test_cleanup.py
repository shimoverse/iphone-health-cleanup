# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline safety invariants; no iPhone, pairing, or device API is used."""
import asyncio
import copy
import importlib.util
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from contextlib import contextmanager

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cleanup.py"
spec = importlib.util.spec_from_file_location("cleanup", SCRIPT)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def app(bid, name, demoted=True, placeholder=True, version="1"):
    return {"CFBundleIdentifier": bid, "CFBundleDisplayName": name,
            "ApplicationType": "User", "CFBundleShortVersionString": version,
            "IsDemotedApp": demoted, "IsPlaceholder": placeholder}


def fixture():
    raw = {"test.shopping": app("test.shopping", "Example Shopping"),
           "test.weather": app("test.weather", "Example Weather"),
           "test.auth": app("test.auth", "Authenticator"),
           "test.mail": app("test.mail", "Example Mail", False, False)}
    inv = {"schema": 1, "device_id": "fake-phone-A", "observed_at": "test", "free_bytes": 100,
           "apps": c.normalize_apps(raw)}
    decisions = {"apps": {bid: {"action": "delete", "category": "ordinary",
                               "reason": "Identity checked; ordinary shopping/weather app"}
                          for bid in ("test.shopping", "test.weather")}}
    return inv, decisions


class FakeDevice:
    def __init__(self, inv, mode="normal"):
        self.device_id = inv["device_id"]
        self.data = copy.deepcopy(inv["apps"])
        self.mode, self.calls, self.reads = mode, [], 0
        self.after_uninstall = False

    async def read_apps(self, ids=None):
        self.reads += 1
        result = copy.deepcopy(self.data)
        if self.mode == "target_changed_between_requests" and self.calls:
            result["test.weather"]["version"] = "new"
        if self.mode == "empty_after_request" and self.after_uninstall:
            result = {}
        if self.mode == "protected_disappears" and self.after_uninstall:
            result.pop("test.auth", None)
        return result if ids is None else {b: a for b, a in result.items() if b in ids}

    async def free_bytes(self):
        return 150

    async def uninstall(self, bid):
        self.calls.append(bid)
        self.after_uninstall = True
        if self.mode == "disconnect_before_effect":
            raise ConnectionError("fake disconnect")
        if self.mode == "false_success":
            return
        self.data.pop(bid, None)
        if self.mode == "disconnect_after_effect":
            raise ConnectionError("fake disconnect")


class PlanningTests(unittest.TestCase):
    def test_inventory_and_plan_do_not_delete(self):
        inv, ds = fixture()
        plan = c.build_plan(inv, ds)
        self.assertEqual(plan["payload"]["targets"], ["test.shopping", "test.weather"])
        self.assertEqual(plan["payload"]["decisions"]["test.auth"]["action"], "keep")
        self.assertEqual(plan["payload"]["decisions"]["test.mail"]["action"], "keep")
        self.assertIn("Needs clarification", c.render_plan(plan))

    def test_sensitive_names_cannot_be_mislabeled_ordinary(self):
        for name in ("MetaMask", "Authenticator", "Binance", "Base App", "Bitwarden", "Gemini", "CA DMV Wallet"):
            with self.subTest(name=name):
                inv, ds = fixture()
                inv["apps"]["test.shopping"] = c.normalize_apps({"test.shopping": app("test.shopping", name)})["test.shopping"]
                with self.assertRaises(c.Refused):
                    c.build_plan(inv, ds)

    def test_explicit_protection_overrides_delete(self):
        inv, ds = fixture()
        ds["protected_bundle_ids"] = ["test.shopping"]
        with self.assertRaises(c.Refused):
            c.build_plan(inv, ds)

    def test_protected_categories_cannot_be_deleted_even_with_unfamiliar_name(self):
        for category in c.PROTECTED_CATEGORIES | {"unknown"}:
            inv, ds = fixture()
            ds["apps"]["test.shopping"]["category"] = category
            with self.subTest(category=category), self.assertRaises(c.Refused):
                c.build_plan(inv, ds)

    def test_installed_and_installing_apps_are_not_offloaded(self):
        for demoted, placeholder in ((False, False), (False, True), (True, False), (None, True), (1, True)):
            inv, ds = fixture()
            inv["apps"]["test.shopping"] = c.normalize_apps({"test.shopping": app("test.shopping", "Example", demoted, placeholder)})["test.shopping"]
            with self.subTest(flags=(demoted, placeholder)), self.assertRaises(c.Refused):
                c.build_plan(inv, ds)

    def test_unclassified_offloaded_app_goes_to_review(self):
        inv, _ = fixture()
        plan = c.build_plan(inv, {"apps": {}})
        self.assertEqual(plan["payload"]["decisions"]["test.shopping"]["action"], "review")
        self.assertFalse(plan["payload"]["targets"])

    def test_unknown_bundle_id_is_rejected(self):
        inv, ds = fixture()
        ds["apps"]["not.in.inventory"] = ds["apps"]["test.shopping"]
        with self.assertRaises(c.Refused):
            c.build_plan(inv, ds)

    def test_edited_status_cannot_enable_deletion(self):
        inv, ds = fixture()
        inv["apps"]["test.mail"]["state"] = "offloaded"
        ds["apps"]["test.mail"] = ds["apps"]["test.shopping"]
        with self.assertRaises(c.Refused):
            c.build_plan(inv, ds)

    def test_identity_mismatch_rejected(self):
        with self.assertRaises(c.Refused):
            c.normalize_apps({"test.one": app("test.two", "Wrong identity")})

    def test_recomputed_digest_still_cannot_remove_protected_app(self):
        inv, ds = fixture()
        plan = c.build_plan(inv, ds)
        p = plan["payload"]
        p["decisions"]["test.auth"] = {"action": "delete", "category": "ordinary", "reason": "bad", "protected": False}
        p["targets"].append("test.auth")
        plan["sha256"] = c.digest(p)
        with self.assertRaises(c.Refused):
            c.validate_plan(plan)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text('{"apps":{},"apps":{}}')
            with self.assertRaises(c.Refused):
                c.read_json(p)

    def test_plan_display_does_not_render_html_from_app_name(self):
        inv, ds = fixture()
        inv["apps"]["test.shopping"]["name"] = "<script>alert(1)</script>|Name"
        text = c.render_plan(c.build_plan(inv, ds))
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)

    def test_app_name_cannot_add_markdown_links_or_images(self):
        inv, ds = fixture()
        inv["apps"]["test.shopping"]["name"] = "![pixel](https://example.com/x) [name](https://example.com/y)"
        text = c.render_plan(c.build_plan(inv, ds))
        self.assertNotIn("![pixel](", text)
        self.assertNotIn("[name](", text)
        self.assertIn(r"\!\[pixel\]\(", text)


class ApplyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.inv, self.ds = fixture()
        self.plan = c.build_plan(self.inv, self.ds)
        self.temp = tempfile.TemporaryDirectory()
        self.journal = Path(self.temp.name) / "journal.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    async def apply(self, dev, token=None):
        return await c.apply_plan(self.plan, self.plan["sha256"] if token is None else token,
                                  dev, self.journal, attempts=3, interval=0)

    async def test_exact_approval_then_only_listed_apps_removed(self):
        dev = FakeDevice(self.inv)
        result = await self.apply(dev)
        self.assertEqual(dev.calls, ["test.shopping", "test.weather"])
        self.assertEqual(result["verified_removed_this_run"], dev.calls)
        self.assertIn("test.auth", dev.data)
        self.assertEqual(result["observed_free_bytes_change"], 50)

    async def test_pilot_and_resume_use_same_approved_plan(self):
        dev = FakeDevice(self.inv)
        pilot = await c.apply_plan(self.plan, self.plan["sha256"], dev, self.journal,
                                   attempts=3, interval=0, limit=1)
        self.assertFalse(pilot["complete"])
        self.assertEqual(pilot["pending"], ["test.weather"])
        result = await self.apply(dev)
        self.assertTrue(result["complete"])
        self.assertEqual(dev.calls, ["test.shopping", "test.weather"])

    async def test_pilot_cannot_complete_on_single_omission_of_unprocessed_app(self):
        dev = FakeDevice(self.inv)
        original = dev.read_apps
        async def omit_unprocessed_on_final_lookup(ids=None):
            result = await original(ids)
            if ids is None and dev.calls:
                result.pop("test.weather", None)
            return result
        dev.read_apps = omit_unprocessed_on_final_lookup
        result = await c.apply_plan(self.plan, self.plan["sha256"], dev, self.journal,
                                    attempts=3, interval=0, limit=1)
        self.assertEqual(result["pending"], ["test.weather"])
        self.assertFalse(result["complete"])
        self.assertIn("test.weather", dev.data)

    async def test_missing_and_wrong_approval_never_delete(self):
        for token in (None, "", "0" * 64):
            dev = FakeDevice(self.inv)
            with self.subTest(token=token), self.assertRaises(c.Refused):
                await c.apply_plan(self.plan, token, dev, self.journal, interval=0)
            self.assertEqual(dev.calls, [])

    async def test_plan_edit_invalidates_approval(self):
        dev = FakeDevice(self.inv)
        self.plan["payload"]["targets"].pop()
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(dev.calls, [])

    async def test_wrong_device_rejected(self):
        dev = FakeDevice(self.inv)
        dev.device_id = "another-phone"
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(dev.calls, [])

    async def test_preflight_all_targets_before_first_delete(self):
        dev = FakeDevice(self.inv)
        dev.data["test.weather"]["state"] = "installed"
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(dev.calls, [])

    async def test_target_changed_mid_batch_stops_before_that_target(self):
        dev = FakeDevice(self.inv, "target_changed_between_requests")
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(dev.calls, ["test.shopping"])

    async def test_false_success_is_not_reported_as_deletion(self):
        dev = FakeDevice(self.inv, "false_success")
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(dev.calls, ["test.shopping"])
        self.assertNotIn('"event": "verified_absent"', self.journal.read_text())

    async def test_empty_targeted_lookup_cannot_fake_success(self):
        dev = FakeDevice(self.inv, "empty_after_request")
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(dev.calls, ["test.shopping"])

    async def test_protected_app_disappearing_stops_batch(self):
        dev = FakeDevice(self.inv, "protected_disappears")
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(dev.calls, ["test.shopping"])

    async def test_disconnect_before_effect_never_blindly_retried(self):
        dev = FakeDevice(self.inv, "disconnect_before_effect")
        with self.assertRaises(ConnectionError):
            await self.apply(dev)
        dev.mode = "normal"
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(dev.calls, ["test.shopping"])

    async def test_disconnect_after_effect_resumes_without_redeleting(self):
        dev = FakeDevice(self.inv, "disconnect_after_effect")
        with self.assertRaises(ConnectionError):
            await self.apply(dev)
        dev.mode = "normal"
        result = await self.apply(dev)
        self.assertEqual(dev.calls, ["test.shopping", "test.weather"])
        self.assertEqual(result["already_absent"], ["test.shopping"])
        self.assertEqual(result["verified_removed_this_run"], ["test.weather"])

    async def test_reinstalled_previously_attempted_app_is_not_deleted_again(self):
        dev = FakeDevice(self.inv)
        await self.apply(dev)
        dev.data["test.shopping"] = self.inv["apps"]["test.shopping"]
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertEqual(len(dev.calls), 2)

    async def test_newly_found_app_never_enters_approved_batch(self):
        dev = FakeDevice(self.inv)
        dev.data["test.new"] = c.normalize_apps({"test.new": app("test.new", "New app")})["test.new"]
        result = await self.apply(dev)
        self.assertIn("test.new", dev.data)
        self.assertNotIn("test.new", result["verified_removed_this_run"])

    async def test_no_deletions_when_retained_anchor_missing(self):
        dev = FakeDevice(self.inv)
        del dev.data["test.mail"]
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertFalse(dev.calls)

    async def test_journal_from_different_plan_rejected(self):
        self.journal.write_text(json.dumps({"plan_sha256": "wrong", "bundle_id": "test.shopping"}) + "\n")
        dev = FakeDevice(self.inv)
        with self.assertRaises(c.Refused):
            await self.apply(dev)
        self.assertFalse(dev.calls)

    async def test_same_device_cannot_run_concurrent_cleanup(self):
        dev = FakeDevice(self.inv)
        with c.device_lock(dev.device_id):
            with self.assertRaises(c.Refused):
                await self.apply(dev)
        self.assertFalse(dev.calls)

    async def test_journal_is_refreshed_after_acquiring_contended_lock(self):
        dev = FakeDevice(self.inv)
        @contextmanager
        def lock_after_other_runner_finished(device_id):
            # Another run wrote intent and disconnected before this lock became available.
            c.Journal(self.journal, self.plan).append("uninstall_intent", "test.shopping")
            yield
        with mock.patch.object(c, "device_lock", lock_after_other_runner_finished):
            with self.assertRaises(c.Refused):
                await self.apply(dev)
        self.assertFalse(dev.calls)


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_library_contract_without_connecting(self):
        try:
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.installation_proxy import InstallationProxyService
        except ImportError:
            self.skipTest("Run with the pinned environment for dependency-contract validation")
        self.assertEqual(c.importlib.metadata.version("pymobiledevice3"), c.PMD_VERSION)
        self.assertTrue(inspect.iscoroutinefunction(create_using_usbmux))
        self.assertIn("autopair", inspect.signature(create_using_usbmux).parameters)
        self.assertIn("connection_type", inspect.signature(create_using_usbmux).parameters)
        self.assertIn("show_placeholders", inspect.signature(InstallationProxyService.get_apps).parameters)
        self.assertIn("bundle_identifiers", inspect.signature(InstallationProxyService.get_apps).parameters)
        self.assertTrue(inspect.iscoroutinefunction(InstallationProxyService.uninstall))

    async def test_adapter_requests_placeholders_and_exact_ids(self):
        inv, _ = fixture()
        raw = {"test.shopping": app("test.shopping", "Example Shopping")}
        svc = mock.Mock()
        svc.get_apps = mock.AsyncMock(return_value=raw)
        dev = c.PmdDevice(inv["device_id"])
        dev.service = svc
        await dev.read_apps(["test.shopping"])
        svc.get_apps.assert_awaited_once_with(application_type="User", show_placeholders=True,
                                            bundle_identifiers=["test.shopping"])

    async def test_unexpected_ids_in_targeted_lookup_rejected(self):
        dev = c.PmdDevice("fake")
        dev.service = mock.Mock()
        dev.service.get_apps = mock.AsyncMock(return_value={"test.other": app("test.other", "Other")})
        with self.assertRaises(c.Refused):
            await dev.read_apps(["test.shopping"])


if __name__ == "__main__":
    unittest.main()

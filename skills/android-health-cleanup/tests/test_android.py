# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline adversarial checks. Every device response is synthetic; no ADB runs."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("android", Path(__file__).parents[1] / "scripts" / "android.py")
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)
SERIAL = "TESTSERIAL"
HELP = "clear [--user USER_ID] [--cache-only] PACKAGE\nuninstall [-k] [--user USER_ID] [--versionCode VERSION_CODE]\n PACKAGE [SPLIT...]\n"
APPS = {"com.example.reader": {"version": 17, "uid": 10123, "installer": "com.android.vending"},
        "com.example.game": {"version": 20, "uid": 10124, "installer": None},
        "com.example.notes": {"version": 1, "uid": 10125, "installer": None}}


class Fake:
    def __init__(self):
        self.apps = copy.deepcopy(APPS)
        self.system = {"com.android.settings"}
        self.calls, self.mutations = [], []
        self.props = {"ro.build.version.sdk": "36", "ro.product.model": "Test device",
                      "ro.product.manufacturer": "Test maker", "ro.build.fingerprint": "test/build:16/release",
                      "ro.build.version.security_patch": "2026-01-01", "ro.vendor.build.security_patch": "",
                      "ro.boot.verifiedbootstate": "green", "ro.boot.flash.locked": "1"}
        self.current, self.aid, self.state, self.help = "0", "abcdef0123456789", "device", HELP
        self.roles, self.settings = {}, {x: "null" for x in a.SETTINGS}
        self.policy = "Current Device Policy Manager state:\n Enabled Device Admins (User 0, provisioningState: 0):\n"
        self.failed, self.reply, self.noop = set(), "Success\n", False
        self.after_mutation, self.hook = None, None
        self.disk = "Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-1 100000 60000 40000 60% /data\n"
        self.power = "Current Battery Service state:\n health: 2\n level: 50\n scale: 100\n temperature: 299\n"

    def __call__(self, argv):
        self.calls.append(argv)
        if self.hook:
            self.hook(argv)
        assert argv[:3] == ["adb", "-s", SERIAL], argv
        cmd = argv[3:]
        if tuple(cmd) in self.failed:
            raise a.Refusal("synthetic unavailable capability")
        if cmd == ["get-state"]:
            return self.state + "\n"
        assert cmd[0] == "shell", argv
        cmd = cmd[1:]
        if cmd == ["am", "get-current-user"]:
            return self.current + "\n"
        if cmd == ["pm", "list", "users"]:
            return "Users:\n UserInfo{0:Owner:c13} running\n UserInfo{10:Work:1030}\n"
        if cmd[0] == "getprop":
            return self.props[cmd[1]] + "\n"
        if cmd[:5] == ["settings", "--user", "0", "get", "secure"]:
            return (self.aid if cmd[5] == "android_id" else self.settings[cmd[5]]) + "\n"
        if cmd[:4] == ["cmd", "role", "get-role-holders", "--user"]:
            return self.roles.get(cmd[-1].rsplit(".", 1)[-1], "")
        if cmd == ["dumpsys", "device_policy"]:
            return self.policy
        if cmd == ["pm", "help"]:
            return self.help
        if cmd == ["df", "-k", "/data"]:
            return self.disk
        if cmd == ["dumpsys", "battery"]:
            return self.power
        if cmd[:3] == ["pm", "list", "packages"]:
            assert cmd[-2:] == ["--user", "0"]
            assert "-u" not in cmd
            if "-s" in cmd:
                return "".join("package:" + p + "\n" for p in sorted(self.system))
            assert cmd == ["pm", "list", "packages", "-3", "-U", "-i", "--show-versioncode", "--user", "0"]
            return "".join("package:{} versionCode:{} installer={} uid:{}\n".format(
                p, d["version"], d["installer"] or "null", d["uid"]) for p, d in sorted(self.apps.items()))
        if cmd[:2] in (["pm", "clear"], ["pm", "uninstall"]):
            self.mutations.append(cmd)
            if self.after_mutation:
                self.after_mutation(cmd)
            if cmd[1] == "uninstall" and not self.noop and self.reply.strip() == "Success":
                self.apps.pop(cmd[-1], None)
            return self.reply
        raise AssertionError("unexpected synthetic command")


def entry(name="com.example.reader", action="uninstall", category="ordinary", display="Reader", reason="User reviewed this exact app"):
    return {"package": name, "action": action, "category": category, "display_name": display, "reason": reason}


class AndroidTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fake = Fake()
        self.device = a.Device(SERIAL, "0", self.fake)
        self.snapshot = self.device.snapshot()
        self.plan = a.make_plan(self.snapshot, [entry()])

    def apply(self, plan=None, limit=2, device=None, approved=None, continuation=False):
        plan = plan or self.plan
        return a.apply_plan(device or self.device, plan, approved or plan["sha256"], self.root / "audit.jsonl", self.root / "state", limit, continuation)

    def test_snapshot_private_binding_and_no_mutations(self):
        raw = json.dumps(self.snapshot)
        self.assertNotIn(self.fake.aid, raw)
        self.assertNotIn(SERIAL, raw)
        self.assertTrue(self.snapshot["protection"]["complete"])
        self.assertEqual(self.snapshot["storage"]["available_bytes"], 40960000)
        self.assertFalse(self.fake.mutations)
        self.assertFalse(any("-u" in argv or "root" in argv for argv in self.fake.calls))

    def test_remote_injection_rejected(self):
        for serial in ("-s", "test;id", "test\n", "x $(id)", "x/../y"):
            with self.subTest(serial=serial), self.assertRaises(a.Refusal):
                a.Device(serial, "0", self.fake)
        for user in ("current", "all", "-1", "00", "0;id", "0\n"):
            with self.subTest(user=user), self.assertRaises(a.Refusal):
                a.Device(SERIAL, user, self.fake)
        for name in ("com.good;id", "--user", "com.good bad", "com.a\n", "com.a/x", "com.a$(id)"):
            with self.subTest(name=name), self.assertRaises(a.Refusal):
                a.make_plan(self.snapshot, [entry(name)])

    def test_sensitive_categories_and_hints_never_override(self):
        for category in a.CATEGORIES - {"ordinary"}:
            with self.subTest(category=category), self.assertRaises(a.Refusal):
                a.make_plan(self.snapshot, [entry(category=category)])
        for name in ("Authenticator", "Banking", "Crypto", "Password manager", "Passkey", "Device Admin"):
            with self.subTest(name=name), self.assertRaises(a.Refusal):
                a.make_plan(self.snapshot, [entry(display=name)])
        kept = a.make_plan(self.snapshot, [entry(action="keep", category="auth")])
        self.assertEqual(kept["decisions"][0]["action"], "keep")

    def test_system_roles_settings_admin_and_additional_are_protected(self):
        with self.assertRaises(a.Refusal):
            a.make_plan(self.snapshot, [entry("com.android.settings")])
        for role in a.ROLES:
            self.fake.roles[role] = "com.example.reader\n"
            with self.subTest(role=role), self.assertRaises(a.Refusal):
                a.make_plan(self.device.snapshot(), [entry()])
            self.fake.roles.clear()
        for setting in a.SETTINGS:
            self.fake.settings[setting] = "com.example.reader" + ("/.Service" if setting != "always_on_vpn_app" else "")
            with self.subTest(setting=setting), self.assertRaises(a.Refusal):
                a.make_plan(self.device.snapshot(), [entry()])
            self.fake.settings[setting] = "null"
        self.fake.policy += " com.example.reader/.Admin: test policy\n"
        with self.assertRaises(a.Refusal):
            a.make_plan(self.device.snapshot(), [entry()])
        with self.assertRaises(a.Refusal):
            a.make_plan(self.device.snapshot(["com.example.reader"]), [entry()])

    def test_unknown_protection_snapshot_partial_apply_blocked(self):
        self.fake.failed.add(("shell", "cmd", "role", "get-role-holders", "--user", "0", "android.app.role.HOME"))
        partial = self.device.snapshot()
        self.assertFalse(partial["protection"]["complete"])
        with self.assertRaises(a.Refusal):
            a.make_plan(partial, [entry()])
        result = self.apply()
        self.assertEqual(result["outcomes"][0]["status"], "preflight_blocked")
        self.assertFalse(self.fake.mutations)

    def test_admin_format_unknown_blocks(self):
        self.fake.policy = "Current Device Policy Manager state:\n"
        self.assertFalse(self.device.snapshot()["protection"]["complete"])

    def test_cache_requires_sdk_and_clear_synopsis(self):
        for sdk, help_text in (("32", HELP), ("36", "clear [--user USER_ID] PACKAGE\n --cache-only appears elsewhere")):
            self.fake.props["ro.build.version.sdk"], self.fake.help = sdk, help_text
            with self.subTest(sdk=sdk), self.assertRaises(a.Refusal):
                a.make_plan(self.device.snapshot(), [entry(action="clear_cache")])
        self.assertFalse(self.fake.mutations)

    def test_uninstall_requires_advertised_version_guard(self):
        self.fake.help = "clear [--user USER_ID] [--cache-only] PACKAGE\nuninstall PACKAGE"
        with self.assertRaises(a.Refusal):
            a.make_plan(self.device.snapshot(), [entry()])

    def test_exact_cache_argv_and_unverified_result(self):
        plan = a.make_plan(self.snapshot, [entry(action="clear_cache")])
        result = self.apply(plan)
        self.assertEqual(self.fake.mutations, [["pm", "clear", "--user", "0", "--cache-only", "com.example.reader"]])
        self.assertEqual(result["outcomes"][0]["status"], "cache_request_accepted_unverified")
        verify = a.verify_plan(self.device, plan)
        self.assertIn("cache_contents_unverified", verify["outcomes"][0]["claim"])

    def test_exact_uninstall_argv_and_independent_verify(self):
        result = self.apply()
        self.assertEqual(self.fake.mutations, [["pm", "uninstall", "--user", "0", "--versionCode", "17", "com.example.reader"]])
        self.assertEqual(result["outcomes"][0]["status"], "uninstall_absence_observed_twice")
        self.assertTrue(a.verify_plan(self.device, self.plan)["outcomes"][0]["expected_state_observed_twice"])

    def test_false_success_is_not_removal_and_stops(self):
        plan = a.make_plan(self.snapshot, [entry(), entry("com.example.game")])
        self.fake.noop = True
        result = self.apply(plan)
        self.assertEqual(len(self.fake.mutations), 1)
        self.assertEqual(result["outcomes"][0]["status"], "request_reported_success_verification_failed")
        self.assertEqual(result["unprocessed"], ["com.example.game"])

    def test_timeout_pending_and_resume_never_reissues(self):
        def timeout(cmd):
            raise a.Refusal("synthetic timeout after request might have arrived")
        self.fake.after_mutation = timeout
        result = self.apply()
        self.assertEqual(result["outcomes"][0]["status"], "pending_request_do_not_retry")
        self.fake.after_mutation = None
        again = self.apply()
        self.assertEqual(again["outcomes"][0]["status"], "pending_request_do_not_retry")
        self.assertEqual(len(self.fake.mutations), 1)

    def test_durable_intent_exists_before_any_mutation(self):
        def check(cmd):
            events = (self.root / "audit.jsonl").read_text().splitlines()
            self.assertEqual(json.loads(events[-1])["phase"], "intent")
            ledger = self.root / "state" / (self.snapshot["anchor"]["serial_hash"] + ".jsonl")
            self.assertEqual(json.loads(ledger.read_text().splitlines()[-1])["phase"], "intent")
        self.fake.after_mutation = check
        self.apply()

    def test_repeat_new_audit_path_still_cannot_reissue(self):
        plan = a.make_plan(self.snapshot, [entry(action="clear_cache")])
        self.apply(plan)
        a.apply_plan(self.device, plan, plan["sha256"], self.root / "other.jsonl", self.root / "state")
        self.assertEqual(len(self.fake.mutations), 1)

    def test_two_app_pilot_preserves_rest_across_resume(self):
        plan = a.make_plan(self.snapshot, [entry(p) for p in APPS])
        result = self.apply(plan)
        self.assertEqual(len(self.fake.mutations), 2)
        self.assertEqual(result["unprocessed"], ["com.example.notes"])
        self.assertEqual(self.apply(plan)["unprocessed"], ["com.example.notes"])
        self.assertEqual(len(self.fake.mutations), 2)
        with self.assertRaises(a.Refusal):
            self.apply(plan, limit=3)

    def test_wrong_serial_user_digest_and_tampering_refused(self):
        with self.assertRaises(a.Refusal):
            a.Device(SERIAL, "10", self.fake)
        for device in (a.Device("OTHER", "0", self.fake),):
            with self.subTest(device=device.user), self.assertRaises(a.Refusal):
                self.apply(device=device)
        with self.assertRaises(a.Refusal):
            self.apply(approved="0" * 64)
        tampered = copy.deepcopy(self.plan)
        tampered["decisions"][0]["package"] = "com.example.game"
        with self.assertRaises(a.Refusal):
            self.apply(tampered)
        self.assertFalse(self.fake.mutations)

    def test_changed_device_hash_build_foreground_or_app_refused(self):
        changes = (("aid", "1234567890abcdef"), ("current", "10"), ("state", "offline"), ("state", "unauthorized"))
        for attribute, value in changes:
            original = getattr(self.fake, attribute)
            setattr(self.fake, attribute, value)
            with self.subTest(attribute=attribute):
                self.assertEqual(self.apply()["outcomes"][0]["status"], "preflight_blocked")
            setattr(self.fake, attribute, original)
        self.fake.props["ro.build.fingerprint"] = "updated/build"
        self.assertEqual(self.apply()["outcomes"][0]["status"], "preflight_blocked")
        self.fake.props["ro.build.fingerprint"] = self.snapshot["anchor"]["build"]
        self.fake.apps["com.example.reader"]["version"] += 1
        self.assertEqual(self.apply()["outcomes"][0]["status"], "preflight_blocked")
        self.assertFalse(self.fake.mutations)

    def test_disconnect_or_anchor_change_between_absence_reads_unverified(self):
        def disconnect(cmd):
            self.fake.state = "offline"
        self.fake.after_mutation = disconnect
        result = self.apply()
        self.assertEqual(result["outcomes"][0]["status"], "pending_request_do_not_retry")
        self.assertEqual(len(self.fake.mutations), 1)

    def test_two_absence_reads_cannot_be_replaced_with_one(self):
        self.fake.noop = True
        plan = self.plan
        def changing(argv):
            if self.fake.mutations and "--show-versioncode" in argv:
                self.fake.apps.pop("com.example.reader", None)
                self.fake.hook = None
        self.fake.hook = changing
        result = self.apply(plan)
        self.assertEqual(result["outcomes"][0]["status"], "uninstall_absence_observed_twice")
        mutation_index = next(i for i, x in enumerate(self.fake.calls) if "uninstall" in x)
        reads = [x for x in self.fake.calls[mutation_index + 1:] if "--show-versioncode" in x]
        self.assertEqual(len(reads), 2)

    def test_journal_corruption_wrong_binding_and_lock_block(self):
        self.root.joinpath("audit.jsonl").write_text('{"kind":"binding","device":"other","user":0}\n')
        self.root.joinpath("audit.jsonl").chmod(0o600)
        with self.assertRaises(a.Refusal):
            self.apply()
        self.root.joinpath("audit.jsonl").unlink()
        state = self.root / "state"
        with a.device_lock(state, self.snapshot["anchor"]["serial_hash"]):
            with self.assertRaises(a.Refusal):
                self.apply()
        self.assertFalse(self.fake.mutations)

    def test_unknown_storage_battery_and_health_enum(self):
        for raw in ("", "Permission denied", "Filesystem 1K-blocks\nx 0 0 0 0% /data", "Filesystem 1K-blocks\nx 10 9 9 1% /data"):
            self.assertIsNone(a.storage(raw)["available_bytes"])
        power = a.battery(self.fake.power)
        self.assertEqual(power["health_state"], "good_enum_not_capacity")
        self.assertIsNone(power["remaining_capacity_percent"])
        self.assertIsNone(power["cycle_count"])
        self.assertIsNone(a.battery(self.fake.power + "UPDATES STOPPED")["charge_percent"])
        self.assertIsNone(a.battery("level: 50")["charge_percent"])

    def test_plan_md_escaped_matches_digest_and_private_files(self):
        plan = a.make_plan(self.snapshot, [entry(display="Reader | <script>`", reason="One\nTwo | three")])
        a.save_report(self.root / "plan.json", plan)
        md = self.root.joinpath("plan.md").read_text()
        self.assertIn(plan["sha256"], md)
        self.assertIn("&#124;", md)
        self.assertNotIn("<script>", md)
        for path in ("plan.json", "plan.md"):
            self.assertEqual(self.root.joinpath(path).stat().st_mode & 0o777, 0o600)
        self.assertEqual(a.checked_plan(a.load(self.root / "plan.json")), plan)

    def test_duplicate_json_and_symlink_refused(self):
        self.root.joinpath("bad.json").write_text('{"x":1,"x":2}')
        with self.assertRaises(a.Refusal):
            a.load(self.root / "bad.json")
        self.root.joinpath("link.json").symlink_to(self.root / "bad.json")
        with self.assertRaises(a.Refusal):
            a.load(self.root / "link.json")

    def test_subprocess_is_bounded_no_shell_and_no_private_error(self):
        response = subprocess.CompletedProcess(["adb"], 0, "device\n", "")
        with patch.object(a.subprocess, "run", return_value=response) as run:
            self.assertEqual(a.execute(["adb", "-s", SERIAL, "get-state"]), "device\n")
            self.assertFalse(run.call_args.kwargs["shell"])
            self.assertEqual(run.call_args.kwargs["timeout"], 20)
        with patch.object(a.subprocess, "run", side_effect=subprocess.TimeoutExpired("PRIVATE_SERIAL", 20)):
            with self.assertRaises(a.Refusal) as raised:
                a.execute(["adb"])
            self.assertNotIn("PRIVATE_SERIAL", str(raised.exception))

    def test_offline_plan_cli_never_constructs_device(self):
        a.write_private(self.root / "snapshot.json", self.snapshot)
        a.write_private(self.root / "decisions.json", [entry()])
        with patch.object(a, "Device", side_effect=AssertionError("no device access allowed")), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(a.main(["plan", "--snapshot", str(self.root / "snapshot.json"), "--decisions", str(self.root / "decisions.json"), "--out", str(self.root / "plan.json")]), 0)

    def test_pending_blocks_other_targets_and_new_plan_replay(self):
        plan = a.make_plan(self.snapshot, [entry(action="clear_cache"), entry("com.example.game")])
        self.fake.after_mutation = lambda cmd: (_ for _ in ()).throw(a.Refusal("synthetic timeout"))
        self.apply(plan)
        self.fake.after_mutation = None
        self.assertEqual(self.apply(plan)["unprocessed"], ["com.example.game"])
        new = a.make_plan(self.snapshot, [entry(action="clear_cache", reason="Fresh review")])
        self.assertEqual(self.apply(new)["outcomes"][0]["status"], "prior_pending_request_do_not_retry")
        self.assertEqual(len(self.fake.mutations), 1)

    def test_explicit_uninstall_continuation_rechecks_pilot(self):
        plan = a.make_plan(self.snapshot, [entry(p) for p in APPS])
        with self.assertRaises(a.Refusal):
            self.apply(plan, continuation=True)
        self.apply(plan)
        self.fake.apps["com.example.reader"] = copy.deepcopy(APPS["com.example.reader"])
        with self.assertRaises(a.Refusal):
            self.apply(plan, continuation=True)
        self.fake.apps.pop("com.example.reader")
        result = self.apply(plan, continuation=True)
        self.assertFalse(result["unprocessed"])
        self.assertEqual(len(self.fake.mutations), 3)

    def test_mixed_continuation_is_guided_and_storage_start_is_first(self):
        plan = a.make_plan(self.snapshot, [entry(action="clear_cache"), entry("com.example.game", action="clear_cache"), entry("com.example.notes")])
        def update(cmd):
            self.fake.disk = self.fake.disk.replace("60000 40000", "50000 50000")
        self.fake.after_mutation = update
        result = self.apply(plan)
        self.assertEqual(result["storage_before"]["available_bytes"], 40000 * 1024)
        self.assertEqual(result["storage_after"]["available_bytes"], 50000 * 1024)
        with self.assertRaises(a.Refusal):
            self.apply(plan, continuation=True)

    def test_zero_exit_stderr_error_is_not_valid_empty_inventory(self):
        response = subprocess.CompletedProcess(["adb"], 0, "", "Permission denied PRIVATE_DATA")
        with patch.object(a.subprocess, "run", return_value=response), self.assertRaises(a.Refusal):
            a.execute(["adb"])

    def test_named_sensitive_package_backstops(self):
        for name in a.SENSITIVE_IDS:
            with self.subTest(package=name), self.assertRaises(a.Refusal):
                a.decision(entry(name, display="Ordinary app"))

    def test_failed_verification_cannot_replay_under_a_new_digest(self):
        self.fake.noop = True
        self.apply()
        fresh = a.make_plan(self.device.snapshot(), [entry(reason="A different reviewed reason")])
        self.assertEqual(self.apply(fresh)["outcomes"][0]["status"], "prior_pending_request_do_not_retry")
        self.assertEqual(len(self.fake.mutations), 1)

    def test_managed_owner_user_zero_mutations_blocked(self):
        for declaration in ("Device Owner:", "Profile Owner (User 10):", "DeviceOwner:"):
            self.fake.policy += "\n" + declaration + " com.example.admin/.Admin\n"
            with self.subTest(owner=declaration), self.assertRaises(a.Refusal):
                a.make_plan(self.device.snapshot(), [entry()])
        self.assertEqual(self.apply()["outcomes"][0]["status"], "preflight_blocked")
        self.assertFalse(self.fake.mutations)


if __name__ == "__main__":
    unittest.main()

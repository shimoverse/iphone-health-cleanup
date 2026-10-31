# Run files and execution

Use one local run directory for inventory, decisions, plan, journal, results and approval notes. Restrict access to it; device IDs and app inventories are private. Do not upload these files to a classifier or other service without separate authorization. The workflow does not require Jev, another model endpoint, a daemon or an automatic deletion schedule.

## Decisions schema

This is a schema example using fictional IDs, not a deletion proposal for a real phone:

```json
{
  "protected_bundle_ids": ["example.actual.wallet.id"],
  "apps": {
    "example.actual.shopping.id": {
      "action": "delete",
      "category": "ordinary",
      "reason": "Verified identity is a shopping app; offloaded metadata confirmed"
    },
    "example.actual.wallet.id": {
      "action": "keep",
      "category": "crypto_wallet",
      "reason": "Protected wallet"
    }
  }
}
```

Copy actual IDs from the inventory. Each decision has exactly `action`, `category`, `reason`. Actions: `delete`, `keep`, `review`. Categories: `ordinary`, `unknown`, `authenticator`, `password_manager`, `crypto_exchange`, `crypto_wallet`, `payment_wallet`, `digital_identity`, `financial_tool`. Only explicitly classified ordinary offloaded apps may be deletion targets. Sensitive categories, exact protected IDs and name-based backstops prohibit deletion. A blocked or unclear identity needs review, not relabeling to get around the check. Additional protected IDs can be supplied; no override for a protection is offered by this cleanup tool.

Planning does not talk to the phone. It creates `plan.json` and a Markdown review next to it. Preserve both files after showing the list. The user approves the exact list; only then copy the printed 64-character SHA-256 into the execution command. A digest/command flag binds a plan but does not authenticate the user: the agent must have the actual approval in the conversation. Keep a local note pointing to that approval and digest.

## Pilot, continue and verify

These are templates, not authorization to run deletion:

```sh
python <skill-dir>/scripts/cleanup.py apply --plan <run-dir>/plan.json --approved-sha256 <approved-digest> --journal <run-dir>/journal.jsonl --out <run-dir>/pilot.json --limit 2
```

After checking the pilot result, continue with the same approved list and journal:

```sh
python <skill-dir>/scripts/cleanup.py apply --plan <run-dir>/plan.json --approved-sha256 <approved-digest> --journal <run-dir>/journal.jsonl --out <run-dir>/result.json
python <skill-dir>/scripts/cleanup.py verify --plan <run-dir>/plan.json --out <run-dir>/verification.json
```

The pilot limit caps new uninstall requests, not the approved target list. A resume checks absence of previously attempted apps; it will not submit a second request for an ID already attempted under that plan. If an attempt is unresolved and the app is still present, prepare a fresh inventory/proposal and obtain new approval before retrying. Never discard or edit a journal to force a retry.

The runner uses a device-specific lock, a durable intent log before each request, bounded per-operation timeouts, and repeated app lookup after deletion. A successful API return alone is insufficient. A retained app is used as an anchor so an empty targeted lookup cannot count as success. It checks all targets before its first uninstall and checks each again immediately before that request. It refuses changed metadata, wrong devices, installed apps and modifications to the plan.

Stdout contains concise counts and result paths. Detailed per-app results stay on disk. Inspect those on an error; do not repeatedly paste a full inventory into the conversation. Progress goes to stderr about every 20 seconds or at the end of the batch.

## Tests

```sh
python -m unittest discover -s <skill-dir>/tests -v
```

All tests use a fake phone or inspect API signatures without connecting. Run in the pinned environment for the dependency-contract test; with plain Python it skips that one test if the dependency is missing. Offline tests cannot establish compatibility with a managed real phone. Record read-only device validation and actual approved pilot results separately.

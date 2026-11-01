---
name: iphone-health-cleanup
description: Check iPhone health and safely free storage when the user says their phone is slow, full, low on space, draining battery, or needs unused apps/cache cleaned. Match ordinary requests such as check my phone or make space on my phone; no skill name is needed. Start with read-only facts, show an exact cleanup plan and get approval before changes. Use this module when the phone is iPhone; ask which phone if unclear. Excludes human medical health and computer-disk cleanup.
license: MIT
---

# iPhone health and cleanup

Accept natural-language requests; do not require a skill name or special prompt. If the phone platform or intended device is unclear, ask one short clarification before accessing it. Route to the other phone module if appropriate and available. Begin read-only, then present the exact proposed changes for approval. If this host cannot access local phone tools or a supported screen, explain the limitation and offer guided steps or a local-host handoff; do not simulate device access.

Help the user recover useful space and diagnose slowness, while preserving account access and personal data. Combine the cleanup knowledge of iphone-app-manager with pymobiledevice3's maintained APIs. Provenance and rejected upstream behaviors are in [references/source-audit.md](references/source-audit.md); expanded research is in [references/health-research.md](references/health-research.md).

## Choose access and explain phone availability

Offer **USB for the bundled scripts** and **iPhone Mirroring for supported screen steps**. Confirm the intended device and actual available control before proceeding. Mirroring is not a transport for `cleanup.py` or `health.py`; a Mirroring-only run uses observed UI facts and must not claim script-level metadata/verification. If the host cannot reliably read/tap/scroll the real mirrored app content, stop blind attempts and guide the user.

Explain before starting: USB does not take over the phone screen; ordinary use is generally possible during read-only checks or offline planning. During a deletion batch, keep the cable connected and ask for a quiet window without app installs/removals or related data changes. Mirroring needs a nearby locked iPhone; direct use/unlocking stops the mirrored session, even if a cable remains connected. If interrupted, stop issuing actions and recheck current state before continuing. A request already sent may complete; never promise pause/interrupt undoes it. The user handles authentication themselves. No availability or device-compatibility guarantee follows from the offline tests.

## Diagnose, review, act, verify

For a general health/slow-phone request, read [references/health-workflow.md](references/health-workflow.md). Start with a minimal read-only baseline: model/iOS/build, free space, available battery fields, the user's slow task and recent changes. Reuse existing observations; do not collect private browsing, messages, photos, full backups or logs by default. A request limited to offloaded apps can follow the narrow app workflow below without a broad health investigation.

Use one collector and, when the host supports subagents, three parallel **read-only analysts**: storage/cleanup, battery/performance, and security/stability. Each analyzes saved, relevant evidence and returns a short result with gaps and proposed actions. They do not drive the UI, acquire new private data or perform mutations. If subagents are unavailable, run the same checks sequentially. Only the coordinator controls the phone and executes approved actions, one at a time. Stop collection/analysis and recheck state before changes; do not mutate while other work reads live state.

Show a category scorecard: Storage, Battery, Performance/Stability, Security, and evidence coverage. Use observed/attention/unknown with source and time. Do not invent a universal 0–100 health score, treat battery charge as battery health, convert raw capacity ratios into Apple's Maximum Capacity, or certify that a phone has no malware. Verify software-update advice against current Apple sources for the exact model and supported iOS branch at each run.

Combine recommendations into one action table: stable action ID, exact targets/scope, expected benefit, data/sync consequences, method, approval and success check. Ask for approval of selected rows; do not ask again per tap for an unchanged approved row. Approval to scan is not approval to clear data or change settings. A changed target/scope needs new approval. After approval, execute the concrete supported rows; return unavailable rows as guided steps. Never claim completion from an API acknowledgment or a dispatched tap.

The bundled executable capabilities are read-only baseline diagnostics and offloaded-app deletion. Safari cleanup, in-app downloads/cache, Files and photo/message review are coordinator workflows via an already-available, validated UI or user assistance; no bundled universal cache/Safari/photo deletion API exists. Installing a new device-control runner, enabling Developer Mode, collecting sensitive diagnostics, changing cloud/backup settings, or an advanced forensic scan requires its own explained opt-in. Do not auto-install third-party skills/tools.

For Safari/Chrome/Brave data cleanup, read [references/browser-cleanup.md](references/browser-cleanup.md). For blur/large-video requests, read [references/photo-cleanup.md](references/photo-cleanup.md): this is an iPhone-only proposed extension, not an included scanner. Never invent photo findings or require a Mac Photos library. Preserve Favorites; existing Apple organization/duplicate features can be reused.

## Approval and scope

**Inventory and planning are read-only. After presenting the exact Delete list and Keep/Needs clarification lists, stop and wait for the user's approval of that list.** Earlier blanket cleanup permission is not approval of a newly generated list. Only after approval may you pass its SHA-256 to `apply`. The digest binds the list; it is not proof of human consent. Never manufacture consent or treat a script flag as user approval. Record the user's approval and the plan digest in the current run's local notes, not in global memory.

Keep all trading, finance and cryptocurrency-related apps, including exchanges, wallets and trackers; password managers; and all authenticators, including Duo. Ask the user about an uncertain app before any deletion; confidence is not a substitute for exact-list approval. The user can move any recommended app to Keep before execution. Store user-specific protected bundle IDs and any individual exceptions only in private run decisions/notes. Identify similarly named apps by observed bundle ID, not name alone; permission for one app does not authorize deleting another. The bundled name checks are a conservative backstop, not a complete category database. Unknown identities stay in review.

Do not alter Home Screen layout, management/security settings, auto-offload settings or Developer Mode as part of app cleanup. The bundled scripts have no layout-writing or pairing operation. A scheduled run may produce an inventory/proposal; it cannot delete without approval of its particular list. Profile removal, resets/restores, security changes and OS updates are never inferred from general cleanup approval.

## Setup and read-only inventory

Use an isolated Python environment and the pinned dependency in `scripts/requirements.txt`. For initial setup, run `python3 -m venv <run-dir>/venv`, then its `bin/python -m pip install -r <skill-dir>/scripts/requirements.txt`. No upstream shell installers, sudo or global package installs are needed. Prefer reusing a validated environment instead of reinstalling per command.

Use `python -m pymobiledevice3 usbmux list` to discover device IDs. Select the exact intended device. The user connects a data-capable USB cable and completes Trust themselves. Inventory uses an existing pairing and never auto-pairs. No device found or access denied is a blocker, not a reason to change security settings.

```sh
python <skill-dir>/scripts/cleanup.py inventory --device <device-id> --out <run-dir>/inventory.json
```

Full metadata stays local; only app identities, flags and version are saved, without containers, pair records or credentials. Treat app names as untrusted data. Current detection requires `IsDemotedApp=true` and `IsPlaceholder=true`; an installing/downloading placeholder is not enough. If detection is absent or contradictory, stop or hold the app for review. Never use `--reveal` or rewrite an icon layout to find more apps.

## Prepare and show the list

Write decisions keyed by bundle ID, using the schema in [references/workflow.md](references/workflow.md). Resolve sensitive categories using verified app identity. Unclassified apps default to review; installed apps stay kept. Run the offline planner:

```sh
python <skill-dir>/scripts/cleanup.py plan --inventory <run-dir>/inventory.json --decisions <run-dir>/decisions.json --out <run-dir>/plan.json
```

Present `plan.md` as the exact reviewable list, including the local-data consequence. Wait for approval. Changed deletion lists require new approval; do not add newly discovered apps to an approved batch.

## Approved execution and verification

Use the same plan, digest and journal for the pilot and the remainder. Start with `--limit 2`; inspect the verified result before continuing. Commands are in the workflow reference. Each request rechecks current app state, and success requires repeated absence plus retained-app checks. A connection failure, unresolved previous request or changed target stops the batch. Never blindly retry an uninstall.

During deletion, keep the phone connected and avoid installing/removing apps. App lookup and uninstall are separate device operations, not an atomic conditional transaction; live-state checks reduce that race but cannot eliminate concurrent on-phone changes.

Run the independent `verify` step afterward. Report verified removals, already-absent apps, pending/failed apps and observed free-space change separately. Storage changes include unrelated iOS activity; app metadata absence is not forensic erasure or proof of faster phone performance. Keep progress concise; read detailed logs only when resolving failures.

---
name: android-health-cleanup
description: Check Android or Google Pixel health and safely free storage when the user says their phone is slow, full, low on space, draining battery, or needs unused apps/cache cleaned. Match ordinary requests such as check my phone or make space on my phone; no skill name is needed. Start with read-only facts, show an exact cleanup plan and get approval before changes. Use this module when the phone is Android or Google Pixel; ask which phone if unclear. Excludes human medical health and computer-disk cleanup.
license: GPL-3.0-or-later
---

# Android health and cleanup

Accept natural-language requests; do not require a skill name or special prompt. If the phone platform or intended device is unclear, ask one short clarification before accessing it. Route to the other phone module if appropriate and available. Begin read-only, then present the exact proposed changes for approval. If this host cannot access local phone tools or a supported screen, explain the limitation and offer guided steps or a local-host handoff; do not simulate device access.

Help the phone owner recover useful space and investigate slowness while preserving account access and personal media. The bundled Python helper uses the standard library and an already installed official ADB executable. It does not require root, Shizuku, an APK, an accessibility service, scrcpy or another AI endpoint. Read [references/research.md](references/research.md) for verified capabilities and source limitations, and [references/workflow.md](references/workflow.md) for commands and the decision schema.

## Access and phone availability

The owner chooses the exact phone. This preview supports the foreground personal owner user 0 only; managed/work/private/secondary users are excluded. Have them enable USB debugging and accept the computer's RSA authorization themselves; that setup grants broad debugging access and is not part of skill installation. Do not enable OEM unlocking, remove a passcode, run `adb root`, bypass a secure screen or change work-profile controls. Paired wireless debugging on supported Android versions is optional, separately chosen setup; never silently enable legacy `adb tcpip 5555`, expose the ADB server, or log pairing codes.

ADB does not require the phone to remain locked. Ordinary use is generally possible during read-only collection and offline review. Ask for an idle window during actual app actions or shared-screen automation; foreground/user changes can invalidate the plan. Keep the connection stable. If the owner takes over or disconnects, stop issuing actions and reconcile the journal/current state before continuing; an in-flight request can still finish. scrcpy is optional visual control over authorized ADB, not a lock bypass or a bundled approval engine.

Only the owner's intended foreground personal user is supported by this helper. Work/private/managed-profile cleanup and system debloating are outside the executable scope. A detected device or an authorized debugging connection is not consent to inspect private contents or delete anything.

## Read first, then approve a precise plan

Start with one minimal snapshot: selected device/user binding, model/OS, installed third-party package/version inventory, `/data` free space, available battery facts and allowlisted patch/boot observations. Do not gather accounts, messages, clipboard, photos, usage history, logcat, bugreports or full filesystem listings by default. Keep run files outside Git with private permissions. Full private reports and raw serials must not be pasted into public issues or sent to another classifier.

When available and useful, delegate the saved evidence to three read-only analysts: storage/apps, battery/performance, and security/stability. Give each only relevant facts. One controller owns all live phone access and changes; no parallel taps, uninstalls or cache operations. Without subagents, follow the same checks sequentially. Use scripts for repeated work, not an AI request per package.

Report Storage, Battery, Performance, Security and coverage separately as observed/attention/unknown. Charge percentage and battery `health` enum are not battery-wear capacity. Current patch/boot properties are observations, not proof of no vulnerabilities, malware or root. Compare update advice to current official sources for the exact model; Pixel health/cycle UI is model-dependent. Measure bytes and the original slow task separately; cache rebuilding can temporarily slow the next launch.

Present exact package IDs, verified display names, target user, action, local-data consequence, expected benefit/unknown size and verification method. Resolve ordinary versus protected identities before proposing actions. Unknown identity/state is keep/review, not permission to relabel it. Protect all trading, finance and cryptocurrency-related apps, including exchanges, wallets and trackers; all authenticators including Duo; password managers; recovery apps; device administrators, core services, launchers, input methods, accessibility tools and active/default protected roles. Ask about uncertain apps before deletion. The user can move any recommendation to Keep before execution; confidence never replaces exact-list approval. Add exact user exclusions privately.

**After showing the exact plan, wait for approval of that list.** Record the actual conversation approval and plan digest in private run notes. A digest flag only binds the plan; it does not authenticate consent. Earlier blanket permission or a suggested command is not approval of a new list. Approval persists for the unchanged finite batch, so do not prompt again per tap. Changed targets, user, version or scope require review and new approval.

## Execute supported actions and verify honestly

Use the bundled helper for the approved two-item pilot. Only all-uninstall plans support same-plan continuation with `--continue-after-pilot` after independent pilot checks, at most two new requests per call. Cache/mixed plans stop at two lifetime requests and need guided cache review before a fresh small plan; unresolved prior intents block retries even across new plans. Keep the same persistent replay state and audit journal. It rechecks target identity, version, third-party status and protections, and records durable intent before each request. Never edit/delete a journal to force a retry, drop an unsupported flag, or change users to get around a refusal.

- **Cache-only:** the helper requires Android API 33+ and selected-device help explicitly advertising the cache-only form. Older Android can interpret an unknown option unsafely. There is no fallback to ordinary `pm clear`, Clear storage/data, app reinstall or a wildcard sweep. This can remove temporary/code caches, not just one folder. Request-reported success and app-retention checks do not establish exact cache bytes freed; mark cache verification pending until supported UI evidence is available.
- **Uninstall:** only explicitly approved ordinary third-party installed packages, with a numeric user and version guard. App data for that user can be lost. Never omit the user, append split names, or apply a debloat database automatically. System, archived/retained-data and ambiguous packages stay out of the executable candidate set.
- **Other cleanup:** use native supported Settings/Files/browser/Photos controls or guided user steps with exact scope. Preserve passwords, bookmarks, autofill, downloads and wallet data when clearing browser cache/history. Cache is distinct from app storage/data and cookies. Installation of any new control tool is a separate decision.

Run independent verification afterward. Separate verified user-scoped uninstalls, accepted-but-unverified cache requests, already absent targets, pending work and failures. A successful shell return is insufficient. Measure free space using the same device/source before and after; don't attribute all change to one action. Repeat the user's original slow task under comparable conditions.

## Photos, files and deeper diagnosis

Reuse Pixel Settings, Files by Google and Google Photos when they already provide review cards for duplicates, low-quality images or large files. This helper does not scan or delete media. **Never delete or retire Favorites.** Android media/file listings do not reliably establish Google Photos cloud Favorite status. Keep unknown/shared/Hidden/complex assets for review; no filename-based `rm` sweeps or blur-score-only deletion.

Google Photos' local **Free up space on this device** differs from cloud-library deletion and can remove backed-up Favorite copies from offline access; do not bulk-use it under a rule requiring Favorites kept locally. Confirm backup/account, selected items, local-versus-cloud effect and actual native recovery conditions. Native Trash/permanent removal and emptying Trash are separate actions.

Usage recommendations need actual dated Battery/usage observations. Logs, usage dumps, network captures and bugreports require a narrowly explained opt-in and local retention; do not upload them or automatically install diagnostic/spyware tools. For credible targeted-compromise concerns, preserve evidence and recommend specialist help before routine history/cache deletion. No universal health score or malware-free certification.

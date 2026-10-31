# Health check and approved actions

Read this for a general iPhone health, slowness or storage request. Keep a narrow offloaded-app request narrow. See [health-research.md](health-research.md) for evidence and reusable project comparisons.

## 1. One baseline, no default private-data sweep

Use an access-restricted local run directory outside any Git checkout. Select the exact already-trusted USB device. Reuse the pinned environment from the app workflow. No automatic pairing, profile installs, Developer Mode changes or passcode changes.

```sh
python <skill-dir>/scripts/health.py snapshot --device <device-id> --out <run-dir>/health-snapshot.json
python <skill-dir>/scripts/health.py report --snapshot <run-dir>/health-snapshot.json --out <run-dir>/health-scorecard.json
```

`snapshot` uses bounded read calls for model/iOS/build, capacity/free space, battery charge and an allowlist of raw battery fields. It uses the same device lock as app deletion and serializes calls. It never gathers logs/backups or modifies the phone. `report` is entirely offline. It produces only a preliminary scorecard, with battery health, usage and security still unknown pending additional evidence. Missing/invalid data cannot pass a check. Non-normalized raw fields remain raw observations, not an Apple health percentage or a temperature diagnosis. No runtime internet call or AI classifier is needed.

Record when the user notices slowness: all apps or one task; on Wi-Fi/cellular/offline; recent iOS update/setup; heat warning; Low Power Mode; battery service message. Use the user's existing description first, then ask only for evidence that changes the next action. One USB read is not a hardware stress test. Avoid mass force-close, RAM cleaners, charging rituals or blindly purging caches.

## 2. Three analysts; one controller

| Worker | Minimal evidence | Output / limits |
|---|---|---|
| Storage / cleanup | Snapshot storage, app inventory, relevant observed Storage settings | Prioritized ordinary offloaded apps and other large cleanup opportunities; account apps protected; installed/unclassified apps not deleted by the runner |
| Battery / performance | Snapshot fields, user symptoms, selected Battery Settings observations | Battery Health/service/peak-performance facts, network/power/heat possibilities, usage-based recommendations only with actual usage evidence |
| Security / stability | Model/iOS/build, current Apple advisory sources, optionally observed profile/update settings and selected reports | Update exposure/posture findings and repeated-crash hypotheses, with coverage; no all-clear malware verdict |

Delegate only to workers available in the host. Give each a focused prompt, explicit read-only role and approved evidence paths. Share normalized summaries before raw data. No worker may install tools, connect independently to the phone, operate Settings, collect more private artifacts, delete, restart or update. The coordinator acquires any additionally approved evidence once, then shares only relevant portions. Final checks use current device state, not a worker's stale snapshot. A local script's file lock does not police other tools: the coordinator must also serialize UI and external-tool use.

Contract for each worker: `findings[{area,status,evidence_source,observed_at,confidence,limitation}], proposed_actions[{id,scope,benefit,consequence,method,verification}], missing_evidence`. Maximum five priority findings and five actions per worker; add detailed evidence by local reference, not full logs in chat. Combine overlapping actions. If subagents add more latency/cost than the check needs, use one agent with the same checklist; parallelism is an option, not proof of savings.

## 3. Clear report, then one specific approval

Use **observed**, **attention**, **unknown** per category and include evidence coverage. No aggregate numerical health score. Battery Maximum Capacity from Settings is a separate Apple-reported metric. An unknown security check remains unknown, including when no indicators or crashes were found.

Present an action table with these columns:

`ID | exact target/scope | benefit/estimated bytes and source | consequence | method/readiness | approval | verification`

Keep recommendations and actions separate: replacing a worn battery is service advice; updating an OS involves compatibility, backup, power and downtime. Do not automatically turn off location/notifications/background features just because an app uses energy. Explain the user benefit/trade-off, then approve a specific setting if warranted.

An approval may select multiple stable action IDs in one reply. Store that reply reference, device, targets, scope, method and observed baseline in private run notes. There is no generic batch executor: the coordinator enforces approvals, while `cleanup.py` also enforces its own exact-plan digest. Reports/action IDs alone are not execution permissions. If new data changes the targets or consequences, refresh the table and approval.

## 4. Action methods and verification

| Action | Supported route | Required scope/consequence | Success check |
|---|---|---|---|
| Ordinary offloaded apps | Existing `cleanup.py` plan/apply/verify | Exact bundle IDs and local app-data loss; preserve sensitive/unknown apps; use unchanged digest/journal and pilot | Repeated absence and retained-app checks; separate free-space observation |
| Safari website data while keeping history | Settings > Apps > Safari > Advanced > Website Data; supported UI or guided user action | One site or all sites, exact profile if offered; cookies/login/offline web data may be lost; no blanket approval to erase history | Reopen relevant website-data view; observe remaining data after refresh; remeasure storage; do not read unrelated browsing content |
| Safari history and website data | Settings > Apps > Safari > Clear History and Website Data; UI or guided user action | Explicit timeframe, profile and tab-close choice; sign-outs; history may clear on other devices with Safari iCloud sync. Cache-only approval does not authorize this row | Observe completion/selected scope via UI, then remeasure; other synced devices not verified unless actually checked |
| In-app cache / offline downloads | The app's own documented storage controls | Exact cache/download set; distinguish removable downloads from chats, account data or originals | Reopen app storage and verify requested items/size; do not delete/reinstall the app as a substitute |
| iCloud Drive local copies | Files > item > Remove Download when present | Exact files; preserve cloud original; distinguish this from Delete | Cloud item remains visible/downloadable; local-download indicator changes |
| Photos/videos, Messages attachments or Files deletion | Native reviewed selection/UI; advanced pipeline not bundled | Exact selected items, backup/recovery status and iCloud sync consequences; photos/attachments may disappear on other devices. Emptying Recently Deleted is a separate permanent deletion action | Check selected items/recovery view and free space; don't count recovery-bin retention as reclaimed space without measurement |
| Settings changes / update / restart | Observed UI or user-assisted, separately scoped | Name precise setting/update/restart and practical effect; user handles passcodes and credentials | Reopen setting or observe new build/reconnected state; task performance measured separately |

Do not use raw AFC unlink as a general Photos-library deletion method, delete arbitrary app sandbox directories, sweep System Data or flush device logs. Ordinary trusted USB file access is not unrestricted filesystem access. Deleting history is neither a malware removal procedure nor a general speed fix.

For UI actions, inspect the current screen before and after each meaningful operation. Use an already-available supported connector first. If Mirroring cannot expose app content or scrolling fails, stop blind retries; give the exact guided step or explain an optional adapter. Do not claim dispatched/uncertain operations succeeded. A user may approve a specific row once; do not request approval for every tap within it. Pause only if scope changes, authentication is required, or a new consequence appears.

Optional XCTest/WDA/iphone-use control needs a separately reviewed local setup, signing/Developer Mode as applicable, and real-device readiness checks. Keep controls local/authenticated. Never weaken passcodes, trust arbitrary profiles, expose an unauthenticated control port, or assume a replay flow's prior success verifies today's action. Commercial/open-use licensing and telemetry settings need checking before adoption; no automatic installation.

## 5. Opt-in logs and forensic checks

Start with Battery Settings activity and selected reports already provided by the user. For additional acquisition, explain the file types, time range, local storage, potential private contents and expected collection cost; get opt-in before collecting. Bound logs by count, bytes and time. Keep raw artifacts local and outside Git; AI subagent context is still model processing, so don't send full raw logs without disclosure and authorization. Don't enable analytics sharing just to obtain a baseline.

For crash copies use the reviewed pymobiledevice3 API with `erase=False`. In the pinned library, `get_new_sysdiagnose()` defaults to `erase=True`: explicitly override it if a separately approved capture is needed. Do not call `clear`, `flush`, broad syslog/packet capture or profile installation as part of a read-only health check. Sysdiagnose is a targeted escalation, not routine cleaning; acquisition itself uses device resources and time. Preserve original logs if compromise is suspected.

For usage analysis, require actual observation dates and collection coverage. Powerlog hourly/daily rollups may duplicate totals; do not sum both. An active-hour count is not launch count or session length. Do not infer low usage from a missing log record. Inventory alone cannot show Screen Time.

Security baseline: compare installed iOS/build to current official releases for that model/branch, check automatic/security update settings and observe VPN & Device Management with consent. Do not remove an unfamiliar work/school profile or VPN automatically. Review Safety Check, account devices and permissions only when the user wants that sensitive scope; credentials remain with the user. Lockdown Mode changes functionality and is a distinct high-risk protection choice, not a performance tweak.

MVT/iLEAPP or encrypted-backup analysis is advanced opt-in, not a default health scan. Audit the chosen release and acquisition method first, establish local encrypted storage and supported Python/runtime requirements, and record modules, evidence coverage, IOC version/time and limitations. A known-indicator match needs expert interpretation; no match does not prove absence of compromise. Do not automatically pair, change backup encryption, install trust/security configuration, upload backups, contact third parties, erase artifacts or declare the phone clean. An Apple threat notification or credible targeted-attack concern calls for specialist guidance and evidence preservation before routine cleanup.

## 6. Verify the outcome users care about

Show completed/verified, pending, failed and user-assisted actions separately. Measure before/after storage from the same source and exact device; refresh after iOS recalculates. Don't add estimated app sizes and storage deltas as if they were the same measure. Note concurrent downloads/photos/iOS activity.

For speed, repeat the specific slow task under comparable power, temperature and network conditions after the phone settles. Report user-observed responsiveness or measured task timing separately from bytes recovered. If speed is unchanged, retain the finding and investigate other causes; do not mark success just because files disappeared. A battery service recommendation cannot be fixed by cache deletion.

Planning time targets (not device benchmarks): ready-connection baseline and compact report roughly 2–5 minutes; guided settings review 5–15 minutes; cleanup depends on selected apps/data and prompts; large backup/sysdiagnose/forensics can take tens of minutes or hours. First-time developer UI setup is extra and optional. Use task-local measurements to replace these targets after a real run.

# Android / Pixel owner workflow

## 1. Install instructions, then authorize a connection separately

Read the root README and this module's SKILL.md. The installer copies local instructions/helpers only: it does not install ADB, connect to a phone, enable debugging, pair wireless devices or install a phone app. Python 3.9+ standard library on Unix is sufficient for the helper; a current Python is recommended. Native Windows execution is not supported in this preview.

Install official Android Platform Tools separately. The phone owner enables Developer options and USB debugging, connects a data-capable cable, unlocks the phone and accepts the computer's RSA authorization prompt. Never enable OEM unlocking or root. `adb devices -l` helps select the exact authorized serial locally; do not pick the first device or publish the list. Android 11+ paired wireless debugging is optional when supported; explicit pairing is distinct from connecting. Do not expose an ADB listener publicly or use legacy TCP enabling as a shortcut.

This preview supports the **foreground personal owner user 0 only**. Work, Private Space, managed, guest and secondary users are outside its mutation scope. A managed owner device is also not a suitable cleanup target. If protection evidence is unavailable or ambiguous, use a guided Settings review rather than weakening checks.

ADB does not reserve the phone screen or make it unavailable. Ordinary use is generally possible during read-only collection and offline planning. Keep a quiet window during app changes and verification. Optional scrcpy shares the foreground with physical use; stop automation when the owner takes over, then re-observe. It cannot bypass secure locks. Keep the cable/network available; disconnecting is not an undo for a submitted request.

## 2. Collect the smallest useful baseline

Create a private run folder outside the repository. Substitute the exact locally selected serial; do not put a real serial in a public example:

```sh
ANDROID_RUN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/android-health.XXXXXX")"
python3 skills/android-health-cleanup/scripts/android.py snapshot --serial YOUR_SERIAL --user 0 --out "$ANDROID_RUN_DIR/snapshot.json"
```

Optional repeatable `--protect com.example.keep` adds exact exclusions. Supply those on the initial snapshot. The helper saves a private JSON snapshot and readable `snapshot.md`. Raw serial and Android ID are not persisted; hashed bindings are still private device-related data. Model/build, installed package inventory and protection facts can also be sensitive. The helper makes no network/model-provider upload; the host assistant's own data handling is separate.

Baseline reads include model/SDK/build, third-party installed packages and versions, `/data` free space, no-argument battery facts, selected patch/boot observations and device-advertised command help. Battery charge is not wear capacity; a battery health enum is not a percentage. Missing/malformed fields stay unknown. Broad logs, accounts, clipboard, messages, photos, usage histories and backups are excluded. A device-policy query is used to identify administrators; only derived protection facts are saved. Its raw output is not a public diagnostic report.

Use separate read-only analysts for storage/apps, battery/performance and security when useful, with one controller for all live access. Reading a package list does not establish app usage or how many bytes an uninstall will reclaim. Verify app display names and purpose in native Settings/Play Store or with the owner; package-name guessing is insufficient.

## 3. Review an exact finite plan

Create `decisions.json` privately as a JSON **array** with exactly these fields per row. These are fictional examples, not a suggested real deletion list:

```json
[
  {"package":"com.example.oldgame","action":"uninstall","category":"ordinary","display_name":"Example Old Game","reason":"Owner confirmed no saved progress is needed"},
  {"package":"com.example.reader","action":"clear_cache","category":"ordinary","display_name":"Example Reader","reason":"Owner selected temporary cache only"},
  {"package":"com.example.vault","action":"keep","category":"password","display_name":"Example Vault","reason":"Protected account access"}
]
```

Allowed actions are `keep`, `clear_cache`, `uninstall`. Categories are `ordinary`, `auth`, `crypto`, `password`, `finance`, `device-admin`, `core`, `unknown`. Only confirmed ordinary apps are executable candidates. Classifying a sensitive app as ordinary is not an override. The helper also rejects protected packages, system/core/shared-UID packages and sensitive name hints. The controller must still resolve identities: no name heuristic catches every account app. Keep unknowns.

```sh
python3 skills/android-health-cleanup/scripts/android.py plan --snapshot "$ANDROID_RUN_DIR/snapshot.json" --decisions "$ANDROID_RUN_DIR/decisions.json" --out "$ANDROID_RUN_DIR/plan.json"
```

Show `plan.md` to the user, plus the target owner user, consequences and evidence gaps. Include exact package IDs and verified display names; distinguish Keep, Needs Review, Cache and Uninstall. Missing protection evidence blocks executable plans. Cache requests require Android API 33+ **and** the selected device's advertised cache-only synopsis. Version-guarded uninstall must be explicitly advertised as well. Unsupported syntax is a refusal, never permission to drop a flag.

**Wait for approval of the exact list.** Uninstall can remove that user's saved data, offline content and app access. Cache can regenerate and temporarily slow the next launch; no exact savings estimate is inferred. Record the actual conversation approval, reviewed digest and scope in private notes. The SHA-256 digest in `plan.json` binds the reviewed file; it does not prove user consent. Changed device/user/build/version/targets need a fresh review and approval. Existing approval covers an unchanged finite batch without per-app questions.

## 4. Approved two-app pilot

Only after actual approval, use the digest displayed in `plan.md`. Do not substitute an automatically approved hash without review:

```sh
python3 skills/android-health-cleanup/scripts/android.py apply --serial YOUR_SERIAL --user 0 --plan "$ANDROID_RUN_DIR/plan.json" --approved-sha256 REVIEWED_DIGEST --journal "$ANDROID_RUN_DIR/journal.jsonl" --out "$ANDROID_RUN_DIR/pilot-result.json" --limit 2
```

The helper rechecks identity/build/user, app version/status and protection immediately before requests. It scopes uninstall to numeric user 0 and one validated package with a server-side version guard. Cache uses the guarded cache-only form, never ordinary data clearing. It does not root, reset, force-stop everything, debloat system apps or clean archived/retained-data records.

Intent is durably recorded before a request under a per-device lock. A persistent private canonical replay ledger is kept under `~/.local/state/android-health-cleanup`; the requested audit journal is separate. Keep both, use the same state location for every run, and never edit/remove them to force a retry. The optional `--state-dir` is for deliberate host storage configuration, not recovery bypass. Multiple controllers, other hosts or external tools are not coordinated by this local lock: do not run them concurrently.

## 5. Verify, then continue where supported

```sh
python3 skills/android-health-cleanup/scripts/android.py verify --serial YOUR_SERIAL --user 0 --plan "$ANDROID_RUN_DIR/plan.json" --out "$ANDROID_RUN_DIR/verification.json"
```

Uninstall verification requires repeated absence reads bracketed by device/user identity checks. Absence is an observation; it is not proof that this particular request caused the removal. Cache verification confirms app retention/version only: **cache contents and bytes freed remain unverified** without supported independent UI evidence. Observe Settings' cache display if available. Do not label cache accepted as cache reclaimed.

For a plan whose non-Keep rows are **all uninstall**, after the initial pilot is independently verified, `apply` can continue the same approved plan using `--continue-after-pilot`, the same digest, journal and state location. Each invocation submits at most two new requests. It rechecks pilot absence and stops on pending/failed requests; do not parallelize calls. For example, repeat the prior `apply` command with the additional flag and a new result path. A changed plan still needs new approval.

**Preview limit for cache/mixed plans:** only the initial two requests are executable under that plan. Remaining rows stay unprocessed. Review cache results through native Settings before preparing a fresh small plan; do not reselect already attempted cache rows or claim automatic full-batch cache verification. This deliberate limit is slower than a broad cleaner and avoids treating a shell Success as proof of safe cleanup.

If a request times out, disconnects or has ambiguous results, stop. A submitted operation may have finished. Read-only verification/reconciliation comes before any fresh plan; unresolved prior intents block re-execution. Preserve the ledgers and seek help rather than deleting records. The helper does not provide an unattended retry/reset command. Any manual resolution must establish the actual phone state and intended next action; do not fabricate a successful journal row.

Report verified removals, accepted-but-unverified cache requests, failures/pending requests, preflight blocks and unprocessed rows separately. Compare free space using the same device-wide source before/after; other activity can change it. No exact per-app cache savings are attributed. Repeat the original slow task under comparable conditions and distinguish storage relief from performance improvement.

## 6. Native browser, files, photos and deeper health review

Use supported native screens (or guided owner actions) with separately reviewed scopes:

| Area | Useful native route | Boundary |
|---|---|---|
| Battery | Pixel Battery health/capacity/cycles on supported Pixel 8a+; Battery Diagnostics on Pixel 6+ | Actual model/UI matters; do not infer wear from charge or promise repaired capacity |
| Security | Security & privacy, Android/security update, Google Play system update, Play Protect | Current model-specific sources; no malware-free certificate or automatic security-setting changes |
| Browsers | Selected browser's own deletion dialog | Cache/history/cookies are distinct. Preserve passwords, bookmarks, autofill, downloads and wallet data; explain sign-outs and sync effects |
| Files | Files by Google duplicate, large-file and suggested-picture cards | Preview exact items; keep the original/best copy; never bulk-delete by filename/size alone |
| Photos/videos | Google Photos local-copy and account-storage screens | Never delete/retire Favorites; no general ADB proof of cloud Favorite status. Backup/account/local-versus-cloud effects must be verified |
| Archived apps | Native app info/archive review | Not interchangeable with broad `pm list packages -u`; no scripted archive classification/deletion here |

Google Photos' bulk local **Free up space** has no established Favorites exclusion and can remove offline Favorite copies. Do not use it under a rule requiring those kept locally. Cloud Delete/Manage storage is a different scope. Read the current recovery UI; do not promise universal undo or empty Trash automatically. No media scanner/deletion engine or Mac Photos-library processing is included.

Logs, usage dumps, screenshots and bugreports are optional sensitive evidence, requiring a specific purpose and opt-in. Keep local, minimize retention and do not upload to public issues. Specialist compromise investigations should preserve evidence before routine history/cache cleanup. End with observed findings, unknowns, verified actions and a prioritized next step—not a synthetic total health score.

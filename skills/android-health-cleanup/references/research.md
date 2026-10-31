# Android / Pixel research and source audit

Researched October 31, 2026. Public documentation and selected source inspection only; no phone, account, APK installation or debugging authorization was accessed. Candidate projects were not installed. Code in this module is original; no upstream implementation, debloat list, binary or personal inventory is bundled. Device compatibility, actual speed and storage recovery remain unverified until an owner's approved real-device run.

## Recommended boundary

| Capability | Route | Limit |
|---|---|---|
| Model/OS/build, storage, charge/battery status, patch/boot facts | Bounded ADB reads | Missing, malformed or denied data stays unknown; no numeric total health score |
| Installed third-party package inventory | Explicit device and numeric foreground user | Not a measure of actual usage or per-app reclaimable space |
| Approved cache-only requests | Guarded API 33+ package command with advertised support | Never fall back to data clearing. A command Success is not independently verified cache-byte reclamation |
| Approved app removal | Exact ordinary installed third-party package, numeric user, version guard | Not system debloating, split removal, archive cleanup or all-user removal |
| Battery health/cycles and usage advice | Pixel Battery Settings and diagnostics | Health/cycle UI documented for Pixel 8a+; Battery Diagnostics for Pixel 6+; determine the actual model |
| Browser cache/history | Native controls, optional validated screen automation | History, cookies, passwords, tabs and synced account data are different scopes |
| Files/photo/video opportunities | Native Files/Photos review cards | No bundled media scanner/deletion engine; Favorites and cloud context must be preserved |
| Screen control | Optional scrcpy or separately audited existing UI tool | Shared foreground, secure-screen and permission limits remain |
| Root, bootloader changes, resets, broad private logs or system removal | Outside normal workflow | No automatic fallback when ordinary access is unavailable |

## ADB and Pixel access

Use the [official ADB guide](https://developer.android.com/tools/adb) and [Platform Tools downloads](https://developer.android.com/tools/releases/platform-tools). ADB requires owner-controlled debugging authorization. Select the exact authorized serial; do not pick the first connected phone. Every device command is scoped with `-s`, and every package mutation with a numeric Android user. The preview requires foreground personal owner user 0; work/private/managed/secondary profiles are excluded.

USB is the simplest initial route. Android 11+ paired wireless debugging is optional; pairing and connection endpoints can differ. Keep pairing codes and private endpoints out of logs/issues. No silent legacy TCP port opening or public ADB listener. Native setup changes are not performed by skill installation.

Unlike iPhone Mirroring, ADB/scrcpy does not require the phone to stay locked. Physical use is generally possible during observation, but UI control shares the foreground and app changes can invalidate a cleanup plan. scrcpy's screen-off option does not bypass a secure lock. Plan a quiet mutation window and stop/recheck when the owner takes over. [scrcpy device behavior](https://github.com/Genymobile/scrcpy/blob/a60891aea193d92e7e5c3942700eca63f9d19a5f/doc/device.md), [connection behavior](https://github.com/Genymobile/scrcpy/blob/a60891aea193d92e7e5c3942700eca63f9d19a5f/doc/connection.md).

## Implementation-critical command findings

**Old cache syntax can wipe app data.** Android 12 r1's `runClear` consumes one option and then invokes user-data clearing. An unknown cache-only option can be ignored. Android 13 r1 explicitly implements cache-only handling; inspected Android 16 source retains it. The reviewed revisions are evidence about those implementations, not a universal guarantee about OEM firmware. [Android 12 source](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-12.0.0_r1/services/core/java/com/android/server/pm/PackageManagerShellCommand.java), [Android 13 source](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-13.0.0_r1/services/core/java/com/android/server/pm/PackageManagerShellCommand.java), [Android 16 source](https://android.googlesource.com/platform/frameworks/base/+/android16-release/services/core/java/com/android/server/pm/PackageManagerShellCommand.java).

Require **both** API >=33 and selected-device `pm help` advertising `--cache-only` in the clear synopsis. Never capability-test by mutating. Keep the numeric user before the cache-only option as an extra old-parser defense, and never retry without the flag. The permitted conceptual form is `pm clear --user USER --cache-only PACKAGE`; there is no full-data-clear action in this helper.

The deeper service can clear internal/external cache, code cache and ART profiles. Low-level failures can be logged while an observer reports success. Therefore report request-reported success, app retention and separately observed free space, not a guaranteed per-app cache delta. [PackageManagerService](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/pm/PackageManagerService.java), [AppDataHelper](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/pm/AppDataHelper.java).

**Uninstall scope must be explicit.** Inspected package-shell code defaults to all users if no user is supplied; extra positional arguments enter a split-removal path with broader scope. Use one validated package plus a numeric user and a supported server-side `--versionCode` guard. Preflight alone is not an atomic conditional uninstall. Don't retain data by silently adding `-k` or assume APK size becomes free space. [AOSP package shell](https://android.googlesource.com/platform/frameworks/base/+/android16-release/services/core/java/com/android/server/pm/PackageManagerShellCommand.java).

**Archived is not the same as installed or retained data.** `pm list packages -u` mixes archived apps and other uninstalled/retained-data records. No archive-only list flag exists in the examined Android 16 shell. This version inventories installed third-party apps and leaves archive cleanup to a separately verified native review. [PackageManager matching flags](https://developer.android.com/reference/android/content/pm/PackageManager), [Google app archiving](https://support.google.com/android/answer/15523443?hl=en).

**Avoid broad diagnostic dumps by default.** `dumpsys diskstats` writes/deletes a small performance-test file and includes cached package statistics; it is neither a literal zero-write probe nor guaranteed current per-app accounting. Prefer `df -k /data` and validate units. [DiskStatsService](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/DiskStatsService.java). Routine snapshots exclude logcat, bugreports, accounts, clipboard, screenshots and usage histories. [Bug-report contents](https://developer.android.com/studio/debug/bug-report).

## Battery, performance and security

The no-argument battery dump exposes status/charge and some other fields, not a universal calibrated battery-wear percentage. Android's `health: 2` is an enum, and charge percentage is remaining charge. A stopped/simulated battery-update state must be labelled untrustworthy rather than treated as a good reading. [BatteryManager](https://developer.android.com/reference/android/os/BatteryManager).

Pixel Settings is the consumer authority for supported capacity/cycle observations. Google currently documents health/cycles on Pixel 8a and later and Battery Diagnostics on Pixel 6 and later; not every older Pixel has those fields. Background work after updates can temporarily affect battery use. [Pixel battery guidance](https://support.google.com/pixelphone/answer/15738128?hl=en), [Battery Diagnostics and drain](https://support.google.com/pixelphone/answer/14101646?hl=en).

Security patch dates and Verified Boot/lock properties are OS-reported observations, not a malware scanner, remote attestation or proof all components are patched. Compare the actual model/build with current [Android security bulletins](https://source.android.com/docs/security/bulletin), [Pixel updates](https://support.google.com/pixelphone/answer/4457705) and Settings' security/Google Play system update state. Review Play Protect and permissions through their native screens. No automatic update, bootloader lock/unlock, flashing or account changes. [Verified Boot states](https://source.android.com/docs/security/features/verifiedboot/boot-flow), [Play Protect](https://support.google.com/googleplay/answer/2812853).

## Native storage, browsers and media

Google distinguishes Clear cache from Clear storage/data; the latter removes app data. Cache can regenerate and next launch can be slower. Use Settings' actual per-app cache display for independent cache verification where available. [Pixel storage guidance](https://support.google.com/pixelphone/answer/2840863?hl=en).

Files by Google already offers review cards for duplicate, large and low-quality files. Keep the original/best retained item, inspect the selection, and do not treat every suggestion or large video as disposable. [Duplicate files](https://support.google.com/files/answer/9764075?hl=en), [large files](https://support.google.com/files/answer/10434652?hl=en), [low-quality pictures](https://support.google.com/files/answer/11544776?hl=en).

Google Photos **Free up space on this device** removes eligible backed-up local copies; ordinary Delete / Manage storage affects a different cloud-library scope. No documented Favorites exclusion was established for the bulk local-copy action, so it cannot satisfy a promise that Favorite copies remain available offline. Preserve Favorites, confirm account/backup/quality/coverage, and approve exact effects. Recovery windows and cloud/device sync consequences must be read from the current UI/docs, not assumed from old advice. [Local-copy removal](https://support.google.com/photos/answer/6128843?co=GENIE.Platform%3DAndroid), [deletion behavior](https://support.google.com/photos/answer/6128858?co=GENIE.Platform%3DAndroid), [account storage management](https://support.google.com/photos/answer/9284827?co=GENIE.Platform%3DAndroid).

Chrome's Android dialog separates cache, cookies, history, tabs, passwords and autofill. Keep credentials, downloads, bookmarks and wallet/site data outside an ordinary history/cache request. Sync can expand deletion beyond one phone. Other browsers use their own verified controls. [Chrome Android deletion](https://support.google.com/chrome/answer/2392709?co=GENIE.Platform%3DAndroid).

## Existing tools and skills inspected

| Source / immutable inspected revision | Useful lessons | Adoption decision |
|---|---|---|
| [scrcpy](https://github.com/Genymobile/scrcpy/tree/a60891aea193d92e7e5c3942700eca63f9d19a5f), Apache-2.0 | Local visual control and device/connection handling | Optional, not bundled. Display latency claims are not cleanup benchmarks |
| [mobile-mcp](https://github.com/mobile-next/mobile-mcp/tree/1025dd070fc934986dec9ea25458b0ab03bc54c7), Apache-2.0 | Structured UI results, bounded navigation and cross-platform interfaces | Current source depends on separate mobilecli and exposes broad destructive tools. Telemetry is on by default; not installed or adopted wholesale |
| [uiautomator2](https://github.com/openatx/uiautomator2/tree/3adba4a59382bf64cf0eee515f9d9102b5acff99), MIT | Selectors, hierarchy and explicit waits | Optional future adapter; starting it pushes helper code on-device, so not baseline read-only setup |
| [Shizuku](https://github.com/RikkaApps/Shizuku/tree/b844bc491f1790c72328e1a8e5b2349f8978f0ea), Apache-2.0, and [Canta](https://github.com/samolego/Canta/tree/e3ed0c9bf90ee6f8bfb7a92ba1e140327cda480f), LGPL-3.0 | Capability checks and user-scoped package state | Not normal prerequisites. Android-version/fork compatibility needs separate review; system removal can break a phone |
| [SD Maid SE](https://github.com/d4rken-org/sdmaid-se/tree/95a673f4c1c5c746a622aa842c066782475c8577), GPL-3.0 code | Unknown-versus-zero cache state, terminal UI verification, separate offline-cache choices | Ideas only; no code/assets copied. Documentation/branding are excluded from its code license grant |
| [UAD NG](https://github.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation/tree/69ca5269151ab0788eae7af851090702974a9153), GPL-3.0 | Package explanations, per-user review plans | Debloat descriptions are hints, never approval or proof of safety. No list or updater imported |
| [DroidRun mobile-harness](https://github.com/droidrun/mobile-harness/tree/a8c7270d4c44d7a9ccbcd07983c16e1545d71fa0), MIT | Small guides/app cards, capability checks, observe–act–verify | Selectively adapted concepts, original implementation. No dependency installer, credential manager, Portal or second agent runtime imported |

Public source revisions and selected manifests/service code were inspected; upstream installers and binaries were not run. This is a selective source audit, not a complete dependency or malware guarantee. Telemetry/credential-heavy frameworks, root debloat, unpinned installers, all-user removal and blanket data clearing were rejected.

## Delivery and validation boundary

The module provides original diagnostics/planning/guarded-action code and fake-device tests. Only all-uninstall plans support same-plan continuation after verified pilot checks; cache/mixed plans stop at two lifetime requests and require native cache review before a fresh small plan. Unresolved request intents block re-execution across changed plans. Both platforms share the same approval/protection/privacy principles while retaining separate executable adapters and host-install folders. The Android helper has no third-party Python dependency; ADB is separately installed under its distribution terms. The repository's GPL-3.0-or-later license covers this original code, not upstream tools.

Run offline tests and a fresh independent review before publishing. Then begin any real-phone validation with owner-approved read-only collection, followed only by a specifically approved small ordinary-app pilot. Report accepted cache requests, independent uninstall verification, evidence gaps and measured storage separately. No end-to-end latency, token savings, battery improvement or storage-recovery benchmark was performed in this research/build stage.

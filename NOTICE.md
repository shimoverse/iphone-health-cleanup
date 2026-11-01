# Credits and third-party notices

Copyright (C) 2026 Phone Health & Cleanup contributors.

The original code and documentation in the current revision are licensed under the MIT License. See [LICENSE](LICENSE) for the full grant, copyright/permission notice requirement and warranty disclaimer. This grant covers our original work; it does not relicense third-party software. Earlier GPL grants remain valid for copies received under those terms.

## Dependencies and research references

The iPhone scripts import and use the separately installed `pymobiledevice3` library. The two upstream skills below informed the workflow through research; their scripts and skill bodies were not copied. These are different relationships, recorded separately in the table.

| Source | License / relationship |
|---|---|
| [pymobiledevice3](https://github.com/doronz88/pymobiledevice3), pinned direct dependency `11.49.0` | GPL-3.0-or-later. Installed separately from its published package. This repository calls its APIs and does not vendor its implementation. Retain its own notices/license when redistributing that dependency. |
| [pymobiledevice3 Device Operator skill](https://doronz88.github.io/pymobiledevice3/guides/codex-device-operator-skill/) | GPL-3.0-or-later source reference for transport, prerequisites and safe device-operation patterns; no skill body copied. |
| [Nolikzero/claude-skills: iphone-app-manager](https://github.com/Nolikzero/claude-skills) | MIT. Conceptual source for app inventory/review and offloaded-app cleanup; no script or skill body copied. |
| [Android SDK Platform Tools / ADB](https://developer.android.com/tools/releases/platform-tools) | User-installed external tool, not bundled. Review Google's download terms; the Android module uses only Python's standard library to call the selected local executable. |
| [AOSP package shell implementation](https://android.googlesource.com/platform/frameworks/base/+/android16-release/services/core/java/com/android/server/pm/PackageManagerShellCommand.java) | Apache-2.0 source reference for command semantics. Original wrapper code; no AOSP implementation copied. |
| [scrcpy](https://github.com/Genymobile/scrcpy) and [DroidRun mobile-harness](https://github.com/droidrun/mobile-harness) | Apache-2.0 and MIT respectively. Referenced optional control tool and workflow-pattern source; not bundled or automatically installed. |
| Other projects cited in the research references | Not bundled or installed. A citation does not relicense or endorse their code. Review their current terms before adoption. |

Android research also includes Google Pixel documentation, mobile-mcp, uiautomator2, Shizuku/Canta, SD Maid SE and UAD NG. Workflow concepts were selectively adapted into original code; these tools, binaries and debloat lists are not bundled. See the [Android research notes](skills/android-health-cleanup/references/research.md) and [iPhone source audit](skills/iphone-health-cleanup/references/source-audit.md) for source links and adaptation decisions.

## iPhone dependency boundary

The iPhone USB helpers import `pymobiledevice3==11.49.0`, licensed GPL-3.0-or-later. Our MIT grant does not change that library's license or grant permission to distribute a combined work under MIT alone. Distribution involving GPL components must satisfy the applicable GPL requirements; separate installation by itself is not a blanket exemption. See the [upstream package metadata](https://github.com/doronz88/pymobiledevice3/blob/v11.49.0/pyproject.toml) and [GNU guidance on combined programs](https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins).

The unmodified GPL v3 text previously used at the repository root is retained in [LICENSES/GPL-3.0-or-later.txt](LICENSES/GPL-3.0-or-later.txt) for reference to the third-party dependency. No dependency source is included here. The MIT label describes our original source, not an assertion that the full iPhone USB stack has only MIT obligations.

Generated run data belongs outside the source checkout; it is not a repository example or a contribution.

Apple, iPhone, Safari, Android, Google Pixel and other product names identify compatibility and referenced controls. This is an independent project, not an official Apple or Google product or an endorsed security/diagnostic service.

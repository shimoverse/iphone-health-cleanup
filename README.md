# iPhone Health & Cleanup

An open-source skill for a local AI assistant that helps you understand a slow or full iPhone, review unused apps, and clean up only what you approve.

**Public preview:** the included scripts have 56 offline safety tests. Their real-iPhone compatibility and time savings have not yet been benchmarked. Start with a read-only check. No Apple endorsement or affiliation.

## The problem it solves

A cloud icon beside an app means iOS has removed the app itself while keeping its documents and data. Those leftover entries can make a phone harder to manage. Reviewing and deleting them one by one means repeated navigation, confirmations and checks.

This project gives your assistant a repeatable process:

1. Read a small set of phone facts and identify offloaded apps.
2. Explain what is known, what is unknown and what might help.
3. Show the exact apps or actions proposed for cleanup.
4. Wait for your approval, then perform supported actions and check the result.

It preserves authenticators, cryptocurrency exchanges and wallets, password managers and other protected account apps. Unclear app identities stay for review.

**Recovered storage and a faster phone are different results.** Battery wear, heat, network conditions and power settings can also explain slowness. The assistant should check the original symptom again after cleanup. [Apple's performance guidance](https://support.apple.com/en-us/102598).

## What works today?

| Capability | Current status |
|---|---|
| Read model, iOS/build, available space and some battery fields over trusted USB | Included script; returned fields depend on the device |
| Produce a preliminary health report | Included script; unavailable evidence stays unknown |
| Inventory offloaded apps and prepare a deletion list | Included script |
| Delete specifically approved ordinary offloaded apps and verify absence | Included script; starts with a small pilot and keeps a resumable log |
| Review Battery Settings, performance symptoms and current security advisories | Assistant workflow; needs relevant observations and current sources |
| Clear selected Safari/Chrome/Brave history or cache | Guided workflow using a supported phone interface or your help; no bundled universal browser-erasure API |
| Find blurry photos or large videos and remove clear mistakes | Planned iPhone-only extension; **no photo scanner or photo-deletion engine is included** |
| A universal health score, guaranteed speed increase or malware-free certificate | Not provided |

Mac Photos-library access is not required. The scripts do not jailbreak the phone, enable Developer Mode, auto-pair it, install profiles or change Home Screen layout. Browser/UI control is optional and must already be available or separately set up with your permission.

## The user journey

![User journey: install, connect, inspect, review, approve, clean, verify and check the symptom](docs/workflow.svg)

When the host supports subagents, storage, battery/performance and security analysts can review the same saved facts in parallel. One controller owns phone access and performs changes in sequence. Without subagents, the same checks run sequentially.

## How much time could it save?

**No measured end-to-end speedup is available yet.** The clearest benefit is avoiding repeated app-by-app navigation and reducing assistant screenshot loops.

For illustration only, if finding, confirming and checking each app takes a person **15 seconds**, the repetitive portion would take:

| Apps to handle | Illustrative manual work | What this workflow changes |
|---|---|---|
| 20 | 5 minutes | One reviewed list replaces repeated navigation |
| 50 | 12.5 minutes | A script submits and verifies the approved requests |
| 100 | 25 minutes | Detailed results stay in local files instead of repeated screenshots |

Those figures are arithmetic examples, not observed human timings or promised savings. USB setup, user review, iOS processing and verification still take time; deletion requests run in sequence. A small list may not repay first-time setup. Record actual duration and before/after free space in your first run before making savings claims. More subagents are not automatically cheaper.

## Before you start

- A Mac with a local assistant that can read files and run Python, such as Codex or Claude Code. The app scripts use a Unix file lock; native Windows execution is not supported. Linux USB setup is not validated here.
- Python **3.11 or newer recommended**, plus Git. The existing offline suite was initially developed on macOS Python 3.9; a current Python avoids its old TLS-library warning.
- An iPhone, a data-capable USB cable and an existing trusted connection. If needed, unlock the phone and complete Apple's Trust prompt yourself. The scripts will not pair automatically.
- A few minutes to review the proposed list. Deleting an app also removes its local saved data.

A browser-only chatbot cannot run these local scripts by itself. Installing this skill neither installs a phone app nor grants phone access.

## Install: ask your agent

Copy this into a local coding assistant:

```text
Install the iPhone Health & Cleanup skill from:
https://github.com/shimoverse/iphone-health-cleanup

Review README.md, NOTICE.md and skills/iphone-health-cleanup/SKILL.md first.
Clone it into a local tools folder. Run tools/install_skill.py --dry-run
for the appropriate host (codex, claude or agents), show the destination,
then install the skill without overwriting any existing skill.
Set up an isolated Python environment with the pinned requirements.
Report setup readiness. Do not connect to my phone, delete anything,
collect logs/backups, or change phone settings during installation.
```

An agent should ask only when the target host, an existing installation, or a new permission needs a decision. The installer copies instructions and helpers; it does not contact a phone or install dependencies globally.

## Install: do it yourself

Open Terminal and run:

```sh
git clone https://github.com/shimoverse/iphone-health-cleanup.git
cd iphone-health-cleanup
python3 tools/install_skill.py --agent codex --dry-run
python3 tools/install_skill.py --agent codex
```

Choose the host you actually use:

| Option | Skill location |
|---|---|
| `--agent codex` | `$CODEX_HOME/skills/iphone-health-cleanup`, or `~/.codex/skills/iphone-health-cleanup` |
| `--agent claude` | `~/.claude/skills/iphone-health-cleanup` |
| `--agent agents` | `~/.agents/skills/iphone-health-cleanup`, for hosts that use this location |

The installer refuses to replace an existing destination. For an update, review the changes and back up the installed folder before replacing it. Start a new assistant session if the skill is not discovered. Other hosts can read [SKILL.md](skills/iphone-health-cleanup/SKILL.md) directly and follow its relative references; automatic discovery depends on the host.

Set up the separate device library in a project-local environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/iphone-health-cleanup/scripts/requirements.txt
```

The direct dependency is pinned to `pymobiledevice3==11.49.0`; transitive dependencies are not fully locked. Review upgrades before using them. No extra paid AI service, Jev connection or API key is required by the scripts. Your assistant's normal usage limits still apply.

## Exact prompts to use

### Start with a read-only health check

```text
Use $iphone-health-cleanup to check my iPhone's storage, available battery
information, performance symptoms and security posture. Show evidence,
unknowns and the most useful next steps. Do not delete data or change
settings. Use parallel read-only analysts only when useful.
```

### Clean up offloaded apps

```text
Use $iphone-health-cleanup to inventory my offloaded apps. Keep
authenticators, exchanges, wallets, password managers and unclear apps.
Show the exact Delete, Keep and Needs Review lists and explain local-data
loss. Wait for my approval of that list, then run a small pilot, continue
the same approved batch if verified, and report the measured result.
```

### Request browser cleanup

```text
Use $iphone-health-cleanup to clear browsing history and cache in the
browsers I select on my iPhone. Preserve passwords, bookmarks, autofill,
downloaded files and wallet data. Explain cookies/sign-outs and any sync
effects before including them. Use available supported controls or give
me guided steps; report what was actually verified.
```

In hosts without `$skill-name` invocation, say “Read the installed iPhone Health & Cleanup SKILL.md and follow it.” You can approve several unchanged action rows together; approval is not requested again for each tap. A changed app list or new consequence needs a fresh decision.

## Read-only commands without an agent

From the cloned repository, create a private temporary run folder outside Git:

```sh
PHONE_RUN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/iphone-health.XXXXXX")"
.venv/bin/python -m pymobiledevice3 usbmux list
```

Choose the exact device ID from that local list, then substitute it for `YOUR_DEVICE_ID`:

```sh
.venv/bin/python skills/iphone-health-cleanup/scripts/health.py snapshot --device YOUR_DEVICE_ID --out "$PHONE_RUN_DIR/health-snapshot.json"
.venv/bin/python skills/iphone-health-cleanup/scripts/health.py report --snapshot "$PHONE_RUN_DIR/health-snapshot.json" --out "$PHONE_RUN_DIR/health-scorecard.json"
.venv/bin/python skills/iphone-health-cleanup/scripts/cleanup.py inventory --device YOUR_DEVICE_ID --out "$PHONE_RUN_DIR/inventory.json"
```

These commands read the phone or create local reports. If the device is unavailable, stop and fix the connection; do not weaken security settings. For planning, approval, the two-app pilot and verification, follow [the app workflow](skills/iphone-health-cleanup/references/workflow.md). This README deliberately does not provide a one-command unattended deletion recipe.

## Your data stays out of this repository

The shipped examples use fictional devices and app IDs. The publication is a fresh source-only repository, with no personal cleanup history, device inventories, pair records, screenshots, photos, backups, credentials or runtime logs.

During use, keep run files outside the checkout. They can contain private device IDs and app names. The scripts do not upload them or call an AI service; an assistant may send the text or images it reads to its own model provider. Review that provider's data settings and share minimal summaries. Logs/backups and photo previews require their own scope decision.

Never attach raw run folders, screenshots, browser history or backups to public issues. The included `.gitignore` and publication checks help catch mistakes; they cannot prove that every future contribution is free of personal information.

## More detail and contributing

- [Skill instructions](skills/iphone-health-cleanup/SKILL.md)
- [Health workflow and capability limits](skills/iphone-health-cleanup/references/health-workflow.md)
- [App approval and execution workflow](skills/iphone-health-cleanup/references/workflow.md)
- [On-phone photo cleanup design — planned](skills/iphone-health-cleanup/references/photo-cleanup.md)
- [Source research](skills/iphone-health-cleanup/references/health-research.md) and [source audit](skills/iphone-health-cleanup/references/source-audit.md)
- [Contributing and offline tests](CONTRIBUTING.md)

## License and credit

This project is licensed under **GPL-3.0-or-later**. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md). The GPL license aligns this distribution with the separately installed GPL-licensed pymobiledevice3 dependency. Nolikzero's iphone-app-manager and the pymobiledevice3 Device Operator skill informed the workflow; their scripts and skill bodies were not copied. Other researched tools are not bundled.

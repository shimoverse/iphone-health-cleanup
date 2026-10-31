# Provenance and selective adaptation

Date: October 31, 2026. Scope authorized: combine useful parts of the two researched workflows into a local reusable cleanup skill and runner. Phone deletion still requires a later exact-list approval.

## Sources reviewed

| Source | Pinned revision | Useful ideas retained |
|---|---|---|
| [Nolikzero/claude-skills, iphone-app-manager](https://github.com/Nolikzero/claude-skills/tree/9a5dcb481dcb0c448b143bf8ca57054e41a59c6a/skills/iphone-app-manager) | `9a5dcb481dcb0c448b143bf8ca57054e41a59c6a` | Read-only inventory, category-based review, explicit destructive-batch confirmation, removal logs, independent presence checks, awareness of offloaded-app data loss |
| [pymobiledevice3 Device Operator](https://github.com/doronz88/pymobiledevice3/blob/d98fb4154855738101f39fb104bad988983aa373/.codex/skills/pymobiledevice3-device-operator/SKILL.md) | `d98fb4154855738101f39fb104bad988983aa373` | Maintained async service API, transport prerequisites, exact-device selection, narrow operations, machine-readable results, current API-signature checks |
| [Upstream offloaded-app lookup issue](https://github.com/doronz88/pymobiledevice3/issues/1602) | Support merged March 11, 2026 | `ShowPlaceholders` lookup and explicit `IsDemotedApp`/`IsPlaceholder` metadata |

The new runner is original code using the library's public operations; upstream scripts and skill bodies were not copied. Nolikzero's source repository is MIT; pymobiledevice3 is GPL-3.0-or-later. This package depends on a separately installed pymobiledevice3 package; preserve that dependency's license and notices when redistributing it. The source links identify conceptual and API provenance, not Apple endorsement.

The original small cleanup repository's 12 files were downloaded and its skill, scripts and references reviewed. The maintainer's skill, relevant references, plugin manifests and app API code were also inspected. The isolated runtime uses the published `pymobiledevice3==11.49.0` package. No downloaded setup script was executed.

## Behaviors deliberately excluded

- The third-party purge's Home Screen rewrite/reveal path, including its layout-changing deletion dry run.
- Its broad claim that installation services cannot expose offloaded apps; the maintained lookup now has a specific option.
- Automatically recording a returned uninstall request as proof of removal.
- Global/unpinned installs, remote shell bootstrap, automatic pairing, Developer Mode changes, profiles, firmware operations, and broad app-container access.
- Runtime AI classification, external telemetry, additional model endpoints and recurring unattended deletion.

## Added for the user's requirements

- The exact Delete list is shown first, and execution waits for explicit approval of that list.
- Approval is bound to a plan digest and one device. The digest is an integrity check, not an authentication mechanism; the agent must have actual user approval.
- Protected category checks, additional exact-ID protections, conservative name checks, unknown-app review, and a prohibition on installed-app deletion.
- Preflight/current-state checks, a two-app pilot mode, durable request logging, no blind retries, per-device locking, and repeated absence verification with retained-app anchors.
- Compact program output to keep repeated inventories and API chatter out of model context.

## Validation boundary

Run the bundled offline tests, the skill validator and the Skill Safety Audit scanner. Review scanner hits in context: text about deletion, package setup and local logging is expected. These checks validate specific program invariants and skill structure; they are not a full dependency security audit or a substitute for the real-phone read-only test and approved pilot. Do not report real removals or guaranteed performance improvements from offline tests.

Verdict: **safe to adapt for this narrowly scoped workflow, with live-device compatibility still unverified**. Any real run begins with a read-only inventory; no app is removed during skill construction or testing.

## Completed checks

- 35 offline tests passed, including actual installed-library signature checks for the pinned API; no live device was contacted.
- The skill structure validator passed. A CLI smoke check produced an offline plan and rejected a mismatched approval digest before opening a device or creating a journal.
- An independent fake-device review reproduced two initial edge cases (journal read before locking, and premature pilot completion) and Markdown link/image injection in app labels. All three were corrected, given regression tests, and independently rechecked successfully.
- The static scanner's two hits were manually reviewed: one describes installing into an isolated venv; the other is the upstream `.codex/skills` URL in this provenance table. Neither indicates a global installer or hidden configuration write in the runner.
- The available test interpreter is macOS Python 3.9.6. Importing the upstream dependency emits urllib3's LibreSSL warning. Offline tests pass; this does not validate HTTP/TLS behavior or real-device access. Prefer a current Python with supported OpenSSL for a fresh deployment. The runner's intended operations use the local trusted USB service, not remote HTTP.

Dependency validation does not freeze all transitive packages or prove their security. The direct device library version is pinned, and a future upgrade requires rerunning the tests and a read-only device compatibility check.

## Health workflow expansion, October 31, 2026

Authorized scope expanded to research and encompass storage, Safari, battery/performance, security posture, usage-based recommendations and parallel analysts, followed by specifically approved actions. This is broader orchestration around the existing narrow deletion engine; it does not introduce a universal cache deletion API or forensic certification. Detailed primary sources, candidate project revisions/licenses, adaptation decisions and implementation limits are in [health-research.md](health-research.md).

Added original `health.py`: an existing-trust exact-USB-device collector for allowlisted model/iOS/build, storage and battery facts, plus an offline preliminary scorecard. It shares the cleanup lock; stops on reader failures; closes clients; never collects logs/backups or calls device mutations. The report preserves source, timestamp, exact-device binding in private JSON and a hashed device reference in Markdown. Invalid/missing provenance is refused; unavailable data remains unknown. Output collision checks protect the input snapshot.

Validation: **56 offline tests pass**, including the pinned API contract, trusted-device refusal, closure, shared health/cleanup lock, actual library disconnect handling, missing evidence, report privacy and input/output collisions. The skill validator and generated-index freshness check pass. A fresh-context independent Codex subagent review found a custom-disconnect handling gap, omitted report provenance and an output-path collision; all three were corrected and covered by regression tests. This is behavior review, not the repository's prescribed pre-merge model route or live-device validation.

The static scanner reports six conservative hits: isolated-venv installation prose, an upstream skill URL, and four descriptions of intentionally approval-gated Safari data cleanup. All were manually inspected. The scripts do not access browser profiles/cookies or install global packages; Safari remains a supported-UI/user-assisted workflow with exact-scope approval. No candidate's installer, control daemon, forensic plugin or media-deletion backend was imported or run on a phone. The security-skill research used only an empty synthetic results directory to establish its false-clean-report problem.

Verdict: **safe to adapt with stated capability limits**. Read-only live compatibility, supported UI readiness, actual storage recovery and responsiveness remain unverified. Optional UI/forensic adapters need their own version-specific review and user opt-in. Do not convert this offline validation into a claim about a user's current battery, security or phone speed.

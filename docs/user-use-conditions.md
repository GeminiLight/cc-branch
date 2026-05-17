# User Use Conditions

This document defines repeatable user boundary conditions for CC Branch. It is a
debugging and QA catalog, not a feature wishlist. Each condition describes a
state a real user can reach, what the product should show, and how an engineer
can reproduce, inspect, and recover it.

Use this together with `docs/ux-state-matrix.md`:

- `ux-state-matrix.md` defines the product meaning of ambiguous states.
- This file defines concrete user conditions that can become bug reports,
  manual QA scenarios, or regression tests.

## Debugging Model

CC Branch has four user-visible sources of truth:

| Layer | Purpose | Typical path or command |
| --- | --- | --- |
| Project config | Shared workspace definition | `.cc-branch/config.yaml` |
| Local state | Machine-local runtime metadata | `.cc-branch/state.yaml` |
| Runtime | Processes CC Branch can inspect or manage | `tmux`, terminal opener |
| Host tools | External CLIs launched by windows | `claude`, `codex`, `gemini`, `cursor`, shells |

When a user reports confusing behavior, first determine which layer is wrong,
missing, stale, or unavailable. Do not collapse every problem into "config is
wrong"; many problems are local runtime or host capability issues.

## Standard Triage Commands

Run these from the project root unless noted.

```bash
cc-branch status --json
cc-branch doctor
cc-branch plan
cc-branch sync --dry-run
```

Runtime-specific checks:

```bash
tmux ls
tmux list-windows -t <session-name>
```

Install and packaging checks:

```bash
python --version
cc-branch --version
cc-branch serve --help
```

Web UI checks:

```bash
cc-branch serve
```

Then open the printed local URL and inspect the Dashboard, Config, and Doctor
views.

## Condition Template

Use this shape when adding new cases:

```text
ID:
User intent:
Setup:
Visible symptom:
Expected UX:
Diagnostics:
Likely causes:
Recovery:
Regression target:
```

## Core Conditions

### UUC-001: Fresh Project Without Config

User intent: try CC Branch in a repository that has never been initialized.

Setup:

- Project directory exists.
- `.cc-branch/config.yaml` does not exist.
- `.cc-branch/state.yaml` does not exist.

Visible symptom:

- CLI cannot produce a workspace plan.
- Web UI should show a setup state, not an empty dashboard.

Expected UX:

- Offer `init` or starter template creation.
- Avoid mentioning tmux, state sync, or config drift before a config exists.

Diagnostics:

```bash
test -f .cc-branch/config.yaml
cc-branch doctor
```

Recovery:

```bash
cc-branch init
cc-branch plan
```

Regression target:

- Status API returns a missing-config state.
- Web UI shows project initialization controls.

### UUC-002: Config Exists, State Missing

User intent: clone a configured project and start using it on a new machine.

Setup:

- `.cc-branch/config.yaml` exists.
- `.cc-branch/state.yaml` is absent.

Visible symptom:

- Some agent windows may need generated session IDs before launch.
- User may think the project is broken because state is missing.

Expected UX:

- Treat local state as recoverable runtime metadata.
- Offer plan/start/write-state flows.
- Do not ask the user to commit state.

Diagnostics:

```bash
cc-branch plan
cc-branch doctor
```

Recovery:

```bash
cc-branch plan --write-state
cc-branch start
```

Regression target:

- Doctor identifies missing generated session IDs when applicable.
- `.gitignore` protects `.cc-branch/state.yaml`.

### UUC-003: Invalid Config YAML Or Schema

User intent: edit config manually and return to the dashboard.

Setup:

- `.cc-branch/config.yaml` exists.
- YAML is invalid or required fields have invalid types.

Visible symptom:

- CLI commands fail before planning.
- Web UI Config page can still show the raw file content.

Expected UX:

- Preserve the user's config content.
- Show exact parse or validation errors.
- Do not silently rewrite invalid content.

Diagnostics:

```bash
cc-branch plan
cc-branch doctor
```

Recovery:

- Fix the YAML or schema error.
- Re-run `cc-branch plan`.

Regression target:

- Config read API returns invalid-config details and raw text.
- Save flow validates before write.

### UUC-004: Tmux Runtime Requested, Tmux Missing

User intent: start a workspace with `runtime: tmux` on a machine without tmux.

Setup:

- Config contains one or more tmux slots.
- `tmux` is not on `PATH`.

Visible symptom:

- Start/attach/restart/stop cannot work for tmux slots.
- Web UI may otherwise look normal because config is valid.

Expected UX:

- Show tmux as unavailable runtime capability.
- Disable tmux lifecycle actions before the user clicks them.
- Explain that terminal-runtime slots can still work.

Diagnostics:

```bash
command -v tmux
cc-branch status --json
cc-branch doctor
```

Recovery:

- Install tmux, or change affected slots to `runtime: terminal`.

Regression target:

- Status payload includes `runtimes.tmux.available: false`.
- Dashboard disables tmux lifecycle buttons and shows the local-machine reason.

### UUC-005: Terminal Runtime Without Tmux

User intent: use CC Branch only to open normal terminal or editor windows.

Setup:

- Config uses `runtime: terminal`.
- `tmux` is absent.
- Selected opener is available.

Visible symptom:

- Doctor may report tmux unavailable, but the user's selected workflow should
  still be valid.

Expected UX:

- Do not block terminal-runtime launch because tmux is missing.
- Make clear that terminal runtime is external and not background-managed.

Diagnostics:

```bash
cc-branch doctor
cc-branch open
```

Recovery:

- Pick an available opener if the configured opener is missing.

Regression target:

- Runtime capability checks distinguish tmux from terminal.

### UUC-006: Configured Tmux Window Missing

User intent: return to a project where some tmux windows were closed manually.

Setup:

- State records windows previously applied.
- Config still includes those windows.
- Runtime inspection cannot find one or more windows.

Visible symptom:

- User sees missing windows.
- Older UX may incorrectly call this config drift.

Expected UX:

- Say the windows are not running.
- Offer a non-destructive Start / update action.

Diagnostics:

```bash
cc-branch sync --dry-run
tmux list-windows -t <session-name>
```

Recovery:

```bash
cc-branch sync
```

Regression target:

- Missing running windows are rendered separately from changed launch specs.

### UUC-007: Running Tmux Window Uses Old Launch Spec

User intent: edit command, agent, cwd, or env in config while old tmux windows
are still running.

Setup:

- Runtime window exists.
- Applied metadata or runtime command differs from the current plan.

Visible symptom:

- Window is running, but it does not match the latest config.

Expected UX:

- Say the running window uses an older launch command.
- Offer Start / update.
- Do not stop or overwrite the user's active process without confirmation.

Diagnostics:

```bash
cc-branch plan
cc-branch sync --dry-run
cc-branch status --json
```

Recovery:

```bash
cc-branch sync
```

Regression target:

- Changed running windows are visible even when no window is missing.

### UUC-008: Running Tmux Window Is Untracked

User intent: attach to a workspace that was created by an older CC Branch
version, manual tmux commands, or copied state.

Setup:

- Runtime window exists.
- Current state lacks matching applied metadata.

Visible symptom:

- User sees a running window but CC Branch cannot prove it came from current
  config.

Expected UX:

- Explain that the window is running but untracked.
- Offer Start / update to write current metadata where safe.

Diagnostics:

```bash
cc-branch status --json
cc-branch sync --dry-run
```

Recovery:

```bash
cc-branch sync
```

Regression target:

- Untracked is not merged into missing or changed.

### UUC-009: Extra Tmux Window Outside Current Config

User intent: remove a window from config and clean up old runtime windows.

Setup:

- Tmux session contains a CC Branch-managed window.
- Current config no longer includes that window.

Visible symptom:

- Extra windows appear in status or Dashboard.

Expected UX:

- Separate this from normal Start / update.
- Require explicit confirmation before stopping extra windows.

Diagnostics:

```bash
cc-branch sync --dry-run
tmux list-windows -t <session-name>
```

Recovery:

```bash
cc-branch sync --stop-removed
```

Regression target:

- Web UI uses a destructive confirmation action for extra tmux windows.

### UUC-010: Mixed Runtime Sync State

User intent: recover a workspace after multiple manual edits and tmux changes.

Setup:

- At least one missing window.
- At least one changed running window.
- At least one untracked window.
- At least one extra window.

Visible symptom:

- A single generic warning hides the real work needed.

Expected UX:

- Show every relevant runtime notice.
- Keep destructive cleanup separate from non-destructive start/update.

Diagnostics:

```bash
cc-branch status --json
cc-branch sync --dry-run
```

Recovery:

```bash
cc-branch sync
cc-branch sync --stop-removed
```

Regression target:

- Dashboard renders missing, changed, untracked, and extra states together.

### UUC-011: Terminal Runtime Is External And Not Reusable

User intent: use `runtime: terminal` and expect it to behave like tmux.

Setup:

- Slot uses `runtime: terminal`.
- User launches it through an opener.

Visible symptom:

- CC Branch cannot reliably restart, stop, attach, or inspect the external
  process after launch.

Expected UX:

- Present terminal runtime as "open externally", not as managed background
  runtime.
- Do not show tmux-style sync or stop semantics for terminal slots.

Diagnostics:

```bash
cc-branch status --json
cc-branch open
```

Recovery:

- Use `runtime: tmux` when persistent managed sessions are required.

Regression target:

- Runtime capability helpers, not raw `runtime == "tmux"` checks, gate actions.

### UUC-012: Selected Opener Missing

User intent: open a workspace in a preferred terminal or editor.

Setup:

- Config or UI selects an opener such as Warp, VS Code, Cursor, Terminal, or
  PowerShell.
- The opener is not installed or not discoverable.

Visible symptom:

- Open action fails locally even though config and runtime are valid.

Expected UX:

- Keep unavailable opener visible but disabled.
- Show a concrete reason and alternatives.

Diagnostics:

```bash
cc-branch doctor
cc-branch open --help
```

Recovery:

- Install the selected opener.
- Select another available opener.

Regression target:

- Opener availability is checked before action dispatch.

### UUC-013: Opener Does Not Support Requested Target

User intent: open a specific slot, window, or project directory with a tool that
does not support that target shape.

Setup:

- Opener exists.
- Target kind is unsupported by that opener.

Visible symptom:

- User expects an open action but the tool cannot express it.

Expected UX:

- Resolve fallback behavior deliberately.
- Show the unsupported target reason instead of doing a surprising open.

Diagnostics:

```bash
cc-branch status --json
cc-branch open --help
```

Recovery:

- Pick an opener that supports the requested target.
- Open the project-level target instead.

Regression target:

- Open intent resolution returns structured unsupported-target information.

### UUC-014: Config Save Conflict

User intent: edit config in the Web UI while another process changes the file.

Setup:

- Web UI loads config.
- Config changes on disk before save.

Visible symptom:

- A naive save would overwrite the newer file.

Expected UX:

- Reject stale save.
- Ask the user to refresh and reapply edits.

Diagnostics:

```bash
stat .cc-branch/config.yaml
```

Recovery:

- Refresh the Config view.
- Reapply edits on the latest file.

Regression target:

- Save API compares the loaded version against current disk state.

### UUC-015: Agent CLI Command Missing

User intent: start an agent window whose CLI is not installed.

Setup:

- Config references an agent command such as `claude`, `codex`, `gemini`, or
  `cursor`.
- The command is absent from `PATH`.

Visible symptom:

- Runtime starts fail or immediately exit.

Expected UX:

- Doctor reports the missing command before start where possible.
- Startup failure should identify the exact command.

Diagnostics:

```bash
cc-branch doctor
command -v <agent-command>
```

Recovery:

- Install the agent CLI.
- Fix `PATH`.
- Change the configured agent profile.

Regression target:

- Doctor checks merged built-in, user, workspace, and project agent profiles.

### UUC-016: Unknown Agent Reference

User intent: reference a custom agent by name.

Setup:

- A window uses `agent: some-name`.
- The merged agent registry has no `some-name` entry.

Visible symptom:

- Planning cannot resolve the command.

Expected UX:

- Report the unknown agent name and where agent definitions can be placed.
- Do not produce a partial runtime plan.

Diagnostics:

```bash
cc-branch plan
cc-branch doctor
```

Recovery:

- Use a built-in agent name.
- Add the custom agent under `.cc-branch/agents.yaml` or config `agents`.

Regression target:

- Planner validation fails before runtime mutation.

### UUC-017: Command Override With Agent Metadata

User intent: define a window with an explicit command but keep agent-related
display metadata.

Setup:

- Window has `command`.
- Window also has an `agent` or agent-like label for display.

Visible symptom:

- Older behavior may incorrectly require a generated agent `session_id`.

Expected UX:

- Explicit command should be treated as the launch source.
- Agent display metadata must not force session bootstrap unless the adapter
  actually owns command generation.

Diagnostics:

```bash
cc-branch plan
cc-branch doctor
```

Recovery:

- Keep explicit command if custom launch behavior is intended.
- Remove misleading agent metadata if not needed.

Regression target:

- Command windows do not require agent-generated session IDs.

### UUC-018: Duplicate Slot Or Window Names

User intent: add multiple windows quickly by copying YAML blocks.

Setup:

- Two slots share the same name, or two windows in a slot share the same title.

Visible symptom:

- Runtime target addressing becomes ambiguous.
- State keys may collide.

Expected UX:

- Fail validation before planning or runtime mutation.
- Identify both duplicate names where possible.

Diagnostics:

```bash
cc-branch plan
cc-branch doctor
```

Recovery:

- Rename slots or windows to unique names.

Regression target:

- Config validation catches duplicate target identity.

### UUC-019: Missing Working Directory

User intent: start a window in a directory that does not exist yet.

Setup:

- Slot or window has `cwd`.
- Directory is missing.

Visible symptom:

- Launch would fail after runtime creation if not caught.

Expected UX:

- Doctor identifies missing paths.
- Safe auto-fix may create directories when requested.

Diagnostics:

```bash
cc-branch doctor
cc-branch doctor --fix
```

Recovery:

- Create the directory manually or use `doctor --fix`.

Regression target:

- Doctor checks slot-level and window-level `cwd`.

### UUC-020: Old Root-Level Config Or State Files

User intent: use a checkout that still contains pre-refactor local files.

Setup:

- Files like `.cc-branch.yaml`, `.cc-branch.state.yaml`,
  `.cc-branch.state.toml`, or backups exist at project root.
- Canonical files live under `.cc-branch/`.

Visible symptom:

- User may not know which file is active.
- The product may warn that local runtime state differs from current config.

Expected UX:

- Canonical paths are `.cc-branch/config.yaml` and `.cc-branch/state.yaml`.
- Ignore root-level legacy files unless a migration command explicitly handles
  them.

Diagnostics:

```bash
ls -la .cc-branch*
cc-branch status --json
```

Recovery:

- Confirm canonical files exist.
- Remove obsolete root-level local files after verifying they are not needed.

Regression target:

- Config resolver does not read root-level legacy files in the clean design.

### UUC-021: Shared Config Versus Local State Confusion

User intent: commit workspace setup for teammates.

Setup:

- `.cc-branch/config.yaml` should be committed.
- `.cc-branch/state.yaml` should remain local.

Visible symptom:

- User is unsure what belongs in git.

Expected UX:

- Doctor and docs clearly distinguish shared config from local state.
- Init or doctor fix keeps state ignored.

Diagnostics:

```bash
git status --short
git check-ignore .cc-branch/state.yaml
```

Recovery:

- Commit `.cc-branch/config.yaml`.
- Ignore `.cc-branch/state.yaml`.

Regression target:

- Generated `.gitignore` includes local state.

### UUC-022: Web UI Assets Missing

User intent: run `cc-branch serve` after installing from source or a partial
package.

Setup:

- Backend is installed.
- Bundled static frontend assets are absent.

Visible symptom:

- `serve` starts incorrectly or reports missing assets.

Expected UX:

- Fail with direct install/build guidance.
- Do not serve a broken blank page.

Diagnostics:

```bash
cc-branch serve
python scripts/build-webui.py
```

Recovery:

- Install a published package.
- Or build web assets and reinstall from source.

Regression target:

- Source packaging honors the documented Web UI build behavior.

### UUC-023: Non-Loopback Web UI Without Token

User intent: expose the Web UI beyond localhost.

Setup:

- `cc-branch serve` binds to a non-loopback host.
- No `--token` or `CC_BRANCH_WEB_TOKEN` is provided.

Visible symptom:

- Server refuses to start.

Expected UX:

- Fail closed with a clear security explanation.
- Tell the user how to provide a token.

Diagnostics:

```bash
cc-branch serve --host 0.0.0.0
cc-branch serve --host 0.0.0.0 --token <token>
```

Recovery:

- Bind to localhost, or provide a token for non-loopback access.

Regression target:

- Web server rejects non-loopback binds without auth.

### UUC-024: Python Version Boundary

User intent: install CC Branch in an environment with Python 3.10, 3.11, or
3.12.

Setup:

- Python interpreter version varies by machine.

Visible symptom:

- Install may fail if package metadata and code syntax disagree.

Expected UX:

- Python 3.10+ installs should be supported if the package declares support.
- Unsupported versions should fail at install time, not at runtime.

Diagnostics:

```bash
python --version
python -m pip install .
```

Recovery:

- Use Python 3.10 or newer.
- Prefer `pipx install cc-branch` for user installs.

Regression target:

- CI tests Python 3.10, 3.11, and 3.12.
- Code avoids syntax unavailable on the minimum supported version.

### UUC-025: Desktop Or Wrapper App Uses A Different Backend Context

User intent: launch CC Branch through a desktop app or wrapper instead of the
CLI.

Setup:

- Wrapper invokes the same backend APIs.
- Environment variables, `PATH`, working directory, or project path may differ
  from the user's shell.

Visible symptom:

- CLI works but desktop or wrapper cannot find tmux, agent CLIs, config, or
  project directory.

Expected UX:

- Backend APIs return structured missing capability or missing project errors.
- Wrapper can surface the same Doctor information as CLI/Web UI.

Diagnostics:

```bash
cc-branch status --json
cc-branch doctor
```

Compare shell `PATH` with the wrapper environment.

Recovery:

- Fix wrapper working directory and environment.
- Use absolute project paths when launching from a wrapper.

Regression target:

- Application layer remains transport-neutral and does not assume argparse,
  Rich, or browser-only behavior.

### UUC-026: User Interrupts Or Partially Applies Sync

User intent: sync a stale workspace, then stop or close the command midway.

Setup:

- Sync starts creating or updating runtime windows.
- Process is interrupted before all targets complete.

Visible symptom:

- Some windows are updated and others remain missing or stale.

Expected UX:

- Next status call should show the remaining concrete deltas.
- State writes should be atomic and recoverable.

Diagnostics:

```bash
cc-branch status --json
cc-branch sync --dry-run
```

Recovery:

```bash
cc-branch sync
```

Regression target:

- State persistence uses repository-backed atomic writes and backups.
- Re-running sync is idempotent for already-applied targets.

## Scenario Bundles

Use these bundles for manual QA before releases.

### New User First Run

1. Start without `.cc-branch/config.yaml`.
2. Initialize from a starter profile.
3. Run `plan`.
4. Start workspace.
5. Open Dashboard.
6. Confirm state is generated locally and ignored by git.

Covers: UUC-001, UUC-002, UUC-021.

### Runtime Capability Boundaries

1. Hide tmux from `PATH`.
2. Load a tmux config.
3. Load a terminal-runtime config.
4. Try Dashboard start/restart/stop/open actions.

Covers: UUC-004, UUC-005, UUC-011.

### Ambiguous Runtime State

1. Start a tmux workspace.
2. Manually close one configured window.
3. Edit one command in config.
4. Create one unmanaged tmux window in the session.
5. Remove one configured window from config.
6. Open Dashboard and run dry-run sync.

Covers: UUC-006, UUC-007, UUC-008, UUC-009, UUC-010.

### Local Tool Mismatch

1. Select an opener that is not installed.
2. Reference an agent CLI that is not on `PATH`.
3. Use a missing `cwd`.
4. Run Doctor and Web UI status.

Covers: UUC-012, UUC-015, UUC-019.

### Packaging And Serve

1. Install from source with Web UI build skipped.
2. Run `cc-branch serve`.
3. Bind Web UI to `0.0.0.0` without a token.
4. Repeat with a token.

Covers: UUC-022, UUC-023, UUC-024.

## Maintenance Rules

- Add a UUC entry when a bug report involves unclear user state.
- Add or update a regression test when a UUC exposes a product invariant.
- Keep destructive actions separate from non-destructive recovery paths.
- Prefer capability language over implementation language in user-facing copy.
- Keep tmux, terminal openers, shells, and agent commands as separate concepts.

# cc-branch Architecture

> Status: this document describes the current shipped architecture, including the typed core, session tooling, and bundled Web UI backend.

## 1. High-level overview

cc-branch now has three public surfaces:

- CLI (`cc-branch`, `ccb`)
- Typed Python API (`load_workspace()`, `plan_workspace()`, `WorkspaceContext`, etc.)
- Web UI backend + bundled static frontend (`cc-branch serve`)

All of them are built on the same internal pipeline:

```text
config file + state file
        |
        v
   config.py / state.py
        |
        v
      models.py
        |
        v
   context.py loads:
   WorkspaceConfig + WorkspaceState
        |
        v
     planner.py
        |
        v
     WorkspacePlan
        |
   +----+---------+-----------+-------------+
   |              |           |             |
   v              v           v             v
runtime.py    doctor.py  sessions.py   webui/server.py
```

## 2. Core typed models

Defined in `cc_branch/models.py`.

### Config-side models

- `DisplayConfig`
- `AgentSpec`
- `WindowConfig`
- `SlotConfig`
- `WorkspaceConfig`

### Plan-side models

- `WindowPlan`
- `SlotPlan`
- `WorkspacePlan`

### State / doctor models

- `WindowState`
- `WorkspaceState`
- `Issue`
- `DoctorReport`

These models are the canonical in-memory representation. File I/O and JSON serialization happen at the edges.

## 3. Config loading

Implemented in `cc_branch/config.py`.

Responsibilities:

- resolve config file path, preferring `.cc-branch.yaml`
- still accept legacy `.cc-branch.yml` and `.cc-branch.toml`
- normalize raw config defaults
- materialize `WorkspaceConfig`
- generate starter config/state via `init_workspace()`

## 4. Shared load pipeline: `WorkspaceContext`

Implemented in `cc_branch/context.py`.

`WorkspaceContext` exists so CLI commands and wrappers do not duplicate the same steps.

It is responsible for:

- selecting config/state paths
- honoring `CC_BRANCH_CONFIG` and `CC_BRANCH_STATE`
- loading `WorkspaceConfig`
- loading `WorkspaceState`
- resolving `WorkspacePlan`
- persisting bootstrapped state updates immediately

This is the main command-time boundary object.

## 5. Planning

Implemented in `cc_branch/planner.py`.

Responsibilities:

- normalize shell slots into a synthetic `main` window
- resolve slot and window working directories
- merge slot/window env vars
- build tmux session names
- resolve session IDs and labels
- apply create/resume behavior through agent adapters
- produce `WorkspacePlan.state_updates`

### Planner output

`WorkspacePlan` contains:

- resolved slot list
- resolved window launch commands
- resolved labels and session IDs
- post-launch commands
- state updates that should be written back to `.cc-branch.state.toml`

## 6. Agent adapters

Implemented in `cc_branch/adapters.py`.

This layer keeps planner logic from turning into a pile of per-agent conditionals.

Current adapter strategies:

- `_NoneAdapter`
- `_FlagResumeAdapter`
- `_InternalResumeAdapter`

Selection is based on `resume_mode`.

Agent definitions are loaded from `cc_branch/agents.yaml` (built-in) and merged with optional user overrides at `~/.cc-branch/agents.yaml` or workspace-local `.cc-branch.agents.yaml`. The registry is implemented in `cc_branch/agent_registry.py`.

This is the main extension point for supporting more CLI-specific launch semantics.

## 7. State persistence

Implemented across:

- `cc_branch/state.py`
- `cc_branch/repository.py`

### `state.py`

Public typed API:

- `load_state()`
- `merge_state()`
- `save_state()`

### `repository.py`

`StateRepository` handles:

- TOML serialization/deserialization
- atomic writes through temp file + replace
- backup creation
- rollback support

This gives the project safer persistence semantics than direct `write_text()` calls.

## 8. Runtime layer

Implemented in `cc_branch/runtime.py`.

Responsibilities:

- create / update tmux sessions and windows
- attach to slot or window targets
- stop and restart workspace targets
- open the dashboard session
- build structured status data
- render plain-text status output

### Backend abstraction

`cc_branch/backends.py` defines the `Backend` protocol and the default `TmuxBackend`.

The current runtime is still tmux-based, but the code no longer hardcodes every operation directly in business logic.

## 9. Session lifecycle layer

Implemented in `cc_branch/sessions.py`.

This is a newer surface that treats sessions as first-class objects.

Capabilities:

- `list_sessions()`
- `inspect_session()`
- `prune_sessions()`
- `restore_session()`

Status values:

- `running`
- `stopped`
- `orphaned`

This layer sits between raw runtime state and user-facing maintenance workflows.

## 10. Diagnostics layer

Implemented in `cc_branch/doctor.py`.

Responsibilities:

- build structured issues for tmux, agent commands, slots, and windows
- render a human-readable doctor report
- apply safe auto-fixes

Current auto-fixes include:

- creating missing cwd paths
- generating missing `session_id` values for `generated_uuid` flows
- updating `.gitignore`

## 11. CLI layer

Implemented in `cc_branch/cli.py`.

Responsibilities:

- help and parser definition
- `init` cold-start UX
- dispatch over `WorkspaceContext`
- render rich tables and human-readable text for sessions and help output
- expose the command surface:
  - workspace commands
  - session commands
  - Web UI command

## 12. Web UI layer

Implemented in `cc_branch/webui/server.py` and packaged assets under `cc_branch/webui/static/`.

Responsibilities:

- serve bundled frontend assets
- expose JSON APIs for status/config/doctor/profile/init/config-save/action
- support `project_path`-scoped requests
- support token/cookie auth for the Web UI and all JSON APIs when configured
- provide a stable backend for desktop wrappers or local browser use

## 13. First-run bootstrap system

Implemented across:

- `cc_branch/bootstrap.py`
- `cc_branch/profiles.py`

Responsibilities:

- detect available agent CLIs
- generate profile-based starter configs
- summarize generated config
- bootstrap state for agents that need generated session IDs
- ensure local state is gitignored

Built-in profiles:

- `solo-dev`
- `ai-pair`
- `minimal`

## 14. Current design constraints

### Shipped constraints

- runtime is still tmux-centric
- shell slots are a config shorthand, not a separate non-tmux runtime
- CLI `serve` refuses non-loopback binds unless `--token` or `CC_BRANCH_WEB_TOKEN` is set
- token-protected Web UI sessions must be opened once via the printed `/?token=...` URL
- Web UI design docs may include future work; only the backend/API described in `docs/webui-spec.md` should be treated as current

### Strong invariants

- planner and runtime both operate on typed models
- state persistence goes through the repository-backed path
- user-facing commands should load through `WorkspaceContext`
- docs must distinguish clearly between shipped behavior and roadmap ideas

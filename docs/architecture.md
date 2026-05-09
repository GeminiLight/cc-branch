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
   config/ + state.py
        |
        v
      models/
        |
        v
   context.py loads:
   WorkspaceConfig + WorkspaceState
        |
        v
     planner/
        |
        v
     WorkspacePlan
        |
        v
application/
   workspace_actions/
   workspace_status.py
   config_workflows/
   diagnostics.py
   state_store.py
        |
   +----+---------+-----------+
   |              |           |
   v              v           v
  cli/       webui/server/   Python callers
```

Root-level modules are intentionally kept as entrypoints, small compatibility
facades, or simple leaf helpers. Subsystems with multiple responsibilities live
in package directories such as `application/`, `cli/`, `doctor/`, `models/`,
`planner/`, `runtime/`, `openers/`, `bootstrap/`, `config/`,
`agent_registry/`, `adapters/`, `profiles/`, `repository/`, and
`webui/server/`.

## 2. Core typed models

Defined in `cc_branch/models/`.

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

## 3. Application layer

Implemented in `cc_branch/application/`.

This is the workflow boundary shared by CLI, Web UI, and local Python callers.
Presentation layers parse requests, call application use cases, and render
results. They do not own runtime orchestration, config save semantics, doctor
collection, or applied-state persistence.

Key modules:

- `workspace_actions/` owns start, launch, restart, stop, open, attach,
  dashboard, sync workflows, and Web UI action dispatch from raw action
  requests.
- `workspace_status.py` owns ready/missing/needs-init/invalid-config status
  query payloads.
- `config_workflows/` owns config read/save/probe/init/profile/opener/agent
  workflows, conflict detection, and validation-before-write.
- `config_validation/` collects structural config issues before normalization
  or runtime execution.
- `diagnostics.py` exposes structured doctor reports and text rendering.
- `state_store.py` centralizes load/mutate/save state updates for application
  workflows.

Application code returns transport-neutral result objects. HTTP status codes,
Rich formatting, argparse errors, and frontend display choices belong at the
edges.

## 4. Config loading

Implemented in `cc_branch/config/`.

Responsibilities:

- resolve the canonical `.cc-branch.yaml` config file path
- reject non-YAML workspace config files
- normalize raw config defaults
- materialize `WorkspaceConfig`
- keep legacy starter-config helpers for compatibility

## 5. Shared load pipeline: `WorkspaceContext`

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

## 6. Planning

Implemented in `cc_branch/planner/`.

Responsibilities:

- normalize single-window terminal slots into a synthetic `title`/`main` window
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
- state updates that should be written back to `.cc-branch.state.yaml`

## 7. Agent adapters

Implemented in `cc_branch/adapters/`.

This layer keeps planner logic from turning into a pile of per-agent conditionals.

Current adapter strategies:

- `NoneAdapter`
- `FlagResumeAdapter`
- `InternalResumeAdapter`

Selection is based on `resume_mode`.

Agent definitions are loaded from layered registries and merged field-by-field:

1. `cc_branch/agents.yaml` built-ins
2. `~/.cc-branch/agents.yaml` user overrides
3. `.cc-branch.agents.yaml` workspace-local overrides
4. `.cc-branch.yaml` project-level `agents` overrides

The registry is implemented in `cc_branch/agent_registry/`, and `load_workspace()` injects the effective profiles into `WorkspaceConfig.agents`. Project configs only need an `agents` section when they override defaults or define project-specific agents.

This is the main extension point for supporting more CLI-specific launch semantics.

## 8. State persistence

Implemented across:

- `cc_branch/state.py`
- `cc_branch/repository/`

### `state.py`

Public typed API:

- `load_state()`
- `merge_state()`
- `save_state()`

### `repository/`

`StateRepository` handles:

- YAML serialization/deserialization
- atomic writes through temp file + replace
- backup creation
- rollback support

This gives the project safer persistence semantics than direct `write_text()` calls.

Application workflows that mutate applied runtime metadata use
`application.state_store.StateStore` instead of open-coded load/modify/save
logic in CLI or Web UI handlers.

## 9. Runtime Layer

Implemented in `cc_branch/runtime/`.

```text
cc_branch/runtime/
  __init__.py      public facade for the historical cc_branch.runtime API
  execution/       workspace execution, lifecycle, dashboard, and status
  backends.py      managed session/window backend protocol and TmuxBackend
  capabilities.py slot runtime capability table
  sync/            desired/applied/runtime synchronization reports
  sessions.py      first-class session list/inspect/prune/restore operations
  shells.py        platform-aware shell command helpers
```

The root modules `runtime_sync.py`, `runtime_capabilities.py`, `backends.py`,
`sessions.py`, and `shells.py` are compatibility facades. New internal code
should import from the owning `cc_branch.runtime.*` module.

CC Branch separates two axes that are easy to conflate:

- **Slot runtime**: how a slot is managed by CC Branch. Today the shipped
  runtimes are `tmux` and `terminal`.
- **Shell command**: what runs inside a terminal process, such as `bash`, `zsh`,
  `pwsh`, `powershell`, or an agent CLI command.

`tmux` is not treated as "the only runtime" in application policy. It is the
runtime that currently exposes the richest capability set: persistent sessions,
multiple windows, background start, attach, stop/restart, sync inspection, and
dashboard composition. A `terminal` slot opens an external process through an
opener and is intentionally not reusable or stoppable by CC Branch.

Responsibilities:

- create / update managed runtime sessions and windows
- open external terminal-runtime processes
- attach to targets when the runtime supports attach
- stop and restart workspace targets when the runtime supports lifecycle control
- open the dashboard session when the runtime supports dashboard composition
- build structured status data
- render plain-text status output

### Runtime Capabilities

`cc_branch/runtime/capabilities.py` defines the shipped runtime capability
table. Business logic should ask capability questions such as:

- `is_managed_runtime(runtime)`
- `is_external_process_runtime(runtime)`
- `supports_background_start(runtime)`
- `supports_attach(runtime)`
- `supports_stop(runtime)`
- `supports_dashboard(runtime)`

Do not add new workflow branches by scattering raw string checks such as
`slot.runtime == "tmux"` through application code. Add or update runtime
capabilities first, then route behavior through the capability helpers.

### Backend abstraction

`cc_branch/runtime/backends.py` defines the `Backend` protocol and the default
`TmuxBackend`.

The default managed backend is still tmux. The backend protocol is the adapter
for session/window operations, while runtime capabilities are the application
policy contract that decides which workflows a runtime can participate in.

## 10. Session lifecycle layer

Implemented in `cc_branch/runtime/sessions.py`.

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

## 11. Diagnostics layer

Implemented across `cc_branch/doctor/` and `cc_branch/application/diagnostics.py`.

Responsibilities:

- build structured issues for tmux, agent commands, slots, and windows
- render a human-readable doctor report
- apply safe auto-fixes

Current auto-fixes include:

- creating missing cwd paths
- generating missing `session_id` values for `generated_uuid` flows
- updating `.gitignore`

## 12. CLI layer

Implemented in `cc_branch/cli/`.

Responsibilities:

- help and parser definition
- `init` cold-start UX
- dispatch over `WorkspaceContext` and application use cases
- render rich tables and human-readable text for sessions and help output
- expose the command surface:
  - workspace commands
  - session commands
  - Web UI command

The CLI must not call runtime mutation helpers directly. Start, attach,
dashboard, launch, restart, stop, open, sync, doctor, and config initialization
go through application modules.

## 13. Web UI layer

Implemented in `cc_branch/webui/server/` and packaged assets under `cc_branch/webui/static/`.

Responsibilities:

- serve bundled frontend assets
- expose JSON APIs for status/config/doctor/profile/init/config-save/action
- support `project_path`-scoped requests
- support token/cookie auth for the Web UI and all JSON APIs when configured
- provide a stable backend for desktop wrappers or local browser use

The Web UI handler owns HTTP routing and JSON serialization. Workspace
semantics live in application use cases, including action loading, target
normalization, open-intent resolution, and terminal-runtime fallbacks.

## 14. First-run bootstrap system

Implemented across:

- `cc_branch/bootstrap/`
- `cc_branch/profiles/`

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

## 15. Current design constraints

### Shipped constraints

- `runtime: tmux` is the persistent managed runtime path used by
  dashboard/attach/stop/sync
- `runtime: terminal` opens visible local terminal windows through configured
  openers and is not treated as a persistent managed session
- Bash/Zsh/PowerShell are shell commands or opener implementation details, not
  slot runtime names
- CLI `serve` refuses non-loopback binds unless `--token` or `CC_BRANCH_WEB_TOKEN` is set
- token-protected Web UI sessions must be opened once via the printed `/?token=...` URL
- Web UI design docs may include future work; only the backend/API described in `docs/webui-spec.md` should be treated as current

### Strong invariants

- planner and runtime both operate on typed models
- state persistence goes through the repository-backed path
- user-facing commands should load through `WorkspaceContext` and then call
  application use cases for workflow behavior
- new workflow behavior belongs in `cc_branch/application/` unless it is purely
  presentation, serialization, or compatibility glue
- docs must distinguish clearly between shipped behavior and roadmap ideas

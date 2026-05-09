# Application Layer Architecture Spec

## Status

In progress. The first application-layer slice has been implemented and should
be treated as the baseline for future refactors.

Completed in the initial slice:

- Structured doctor reports are produced once and rendered at the edge.
- CLI JSON status and Web UI status share `application.workspace_status`.
  Web UI status now delegates missing, needs-init, ready, and invalid-config
  query states to that application module.
- Web UI doctor responses now delegate missing, needs-init, ready structured
  reports, and invalid-config states to `application.diagnostics`.
- Runtime inspection goes through `backends.Backend` instead of direct tmux
  subprocess calls above the backend boundary.
- Runtime-applied state writes go through `application.state_store.StateStore`.
- `sync` is a shared `application.workspace_actions.sync_workspace` use case for
  CLI and Web UI.
- `stop`, `restart`, and background `launch` now have shared
  `application.workspace_actions` use cases for the tmux/runtime-state paths.
- `open` now has a shared `application.workspace_actions.open_workspace` use
  case. CLI and Web UI both use it for opener side effects, target handling,
  terminal-runtime behavior, and applied-state persistence.
- Web UI terminal-runtime `launch` and `restart` target fallbacks also route
  through the shared open use case instead of keeping local opener workflow
  helpers.
- Web UI config read, project probe, init, profile, opener, agent, and config
  save queries now route through `application.config_workflows`, including
  optimistic conflict detection, validation-before-write, diagnostics, and file
  version metadata.
- CLI init now routes environment inspection, minimal initialization, and
  profile-based workspace file creation through `application.config_workflows`.
- CLI foreground start, attach, dashboard, and doctor text rendering now route
  through application use cases instead of direct runtime or legacy doctor
  wrappers.
- Web UI action POST handling now routes through
  `application.workspace_actions.execute_workspace_action`, so the HTTP handler
  no longer owns config/state loading, plan construction, target normalization,
  open-intent resolution, or terminal-runtime action fallbacks.
- Architecture tests now guard tmux subprocess isolation and prevent CLI/Web UI
  from owning sync planning, direct state writes, or direct runtime restart
  orchestration. CLI is guarded against re-owning opener side effects, and Web
  UI is guarded against re-owning config save workflow details. Additional rules
  prevent CLI from re-owning runtime mutation, doctor rendering, or init
  workflows, and prevent Web UI from re-owning action dispatch/loading logic.
- `application.config_validation` now collects structural validation issues for
  unknown fields, invalid enum values, invalid scalar types, duplicate names,
  invalid container shapes, invalid env keys, and missing launch commands.
  Unknown fields are warnings; structural errors block config saves before
  runtime execution.
- The Web config editor now surfaces application validation issues on initial
  load and failed saves, so config quality feedback is visible at the product
  edge instead of being limited to API payloads or toast messages.

## Executive Summary

cc-branch has grown from a CLI-first tool into a multi-surface product:

- CLI commands
- Typed Python API
- Web UI HTTP backend
- Desktop sidecar that reuses the Web UI backend

The current codebase already has useful building blocks: typed models, a
planner, agent adapters, a state repository, and a partial tmux backend
abstraction. The main architectural problem is not the absence of layers. The
problem is that application behavior is implemented in the product surfaces.

This spec proposes a staged extraction of application use cases. The intent is
to make CLI, Web UI, desktop, and Python API share the same workflow semantics
without a risky big-bang rewrite.

## Quality Bar

This refactor is only successful if it improves behavior safety and future
change cost. It should not be treated as a directory reshuffle.

Required properties:

- One workflow implementation per user action.
- Transport-independent application results.
- Runtime-specific operations behind backend interfaces.
- Structured diagnostics and validation before text rendering.
- Centralized state mutation for runtime-applied metadata.
- Existing CLI, Web UI, config, and Python API behavior preserved unless a
  compatibility break is explicitly documented.

## Problem

Historically, user-facing workflows such as launch, restart, open, sync,
status, doctor, config save, and state persistence were implemented directly in
the former `cc_branch/cli.py` module and, before the server package split,
repeated in the former `cc_branch/webui/server.py` module.

That creates three concrete risks:

- Behavior drift: a workflow fixed in CLI can stay broken in Web UI, or the
  reverse.
- Low test leverage: core behavior is often tested through argparse or HTTP
  handler tests instead of direct use-case tests.
- Runtime coupling: tmux inspection and execution details leak above the runtime
  boundary, which makes future runtime support harder.

## Goals

- Extract shared application use cases for workspace actions, status, doctor,
  config read/write, and project initialization.
- Keep presentation layers thin:
  - CLI parses args, calls use cases, renders text, and maps results to exit
    codes.
  - Web UI handles HTTP routing, auth, CORS, static files, request parsing, and
    JSON serialization.
  - Desktop uses the same backend contract as Web UI.
- Keep runtime execution and runtime inspection behind backend interfaces.
- Return structured results from application code and render text only at the
  edge.
- Add architecture tests that prevent the old coupling from returning.

## Non-Goals

- Do not rewrite the whole package.
- Do not move files only to match a textbook layered architecture.
- Do not introduce a dependency injection framework.
- Do not replace `http.server` as part of this spec.
- Do not replace tmux as the default runtime.
- Do not break existing `.cc-branch/config.yaml` files.
- Do not remove current public Python APIs such as `load_workspace()`,
  `plan_workspace()`, and `WorkspaceContext`.

## Current Issues

### 1. Workflow Logic Lives In Presentation

`cli.py` owns command parsing, command workflow decisions, runtime calls, state
persistence, and text output.

The former `webui/server.py` module duplicated a large subset of the same logic for HTTP actions,
including launch, restart, open target, open workspace, sync, stop, config save,
and project initialization.

Expected direction: both surfaces call the same application use cases.

### 2. Runtime Boundary Is Leaky

`backends.py` defines a backend protocol, but some modules still execute tmux
subprocesses directly for inspection.

Expected direction: code above the runtime layer asks a backend for runtime
state. It does not know the tmux command line.

### 3. Typed Models Do Not Provide Strong Enough Validation

The dataclasses are helpful, but many fields are plain strings and `from_dict`
methods silently ignore unknown fields.

Expected direction: parsing, normalization, validation, and planning become
distinct steps:

```text
raw config -> parsed config -> validation issues -> normalized config -> plan
```

Invalid enum values and impossible configs should fail before runtime. Unknown
fields can start as warnings to preserve compatibility, then become errors in a
major release.

### 4. Structured Data Is Flattened Too Early

Doctor has `DoctorReport` and `Issue` models, but the public builder returns a
formatted string. This makes the Web UI parse or display text when it should be
able to use structured issue data.

Expected direction: builders return structured objects, renderers return text.

### 5. State Updates Are Too Easy To Bypass

State writes are atomic, but workflow code still performs load/modify/save in
multiple places. The same applied-result persistence logic exists in both CLI and
Web UI.

Expected direction: application use cases own state mutation. Presentation code
does not call `save_state()` for workflow side effects.

## Architecture Direction

Use a strangler pattern. Add an application layer around the existing modules
first. Move or rename lower-level modules only when the boundary is proven.

Initial target:

```text
cc_branch/
  application/
    __init__.py
    commands.py          # request dataclasses
    results.py           # result dataclasses
    workspace_actions.py # launch/restart/stop/open/sync use cases
    workspace_status.py  # status and plan queries
    config_workflows.py  # config load/save/probe/init use cases
    diagnostics.py       # doctor use cases, not text rendering
    renderers.py         # text renderers for CLI compatibility
    ports.py             # protocols only when existing APIs are insufficient

  backends.py            # remains the runtime backend implementation boundary
  runtime.py             # keeps runtime operations during the transition
  state.py               # keeps compatibility API during the transition
  cli.py                 # presentation
  webui/server/          # presentation and HTTP transport
```

Avoid creating `domain/` and `infrastructure/` directories in the first PR. Those
directories may be useful later, but adding them now would create migration
surface without solving the duplication problem.

## Application Use Cases

The application layer may be implemented as service classes or module-level use
case functions. Prefer the simplest form that keeps behavior testable and shared.

### Workspace Actions

Required requests:

```python
@dataclass(frozen=True)
class LaunchRequest:
    project_dir: Path
    config_path: Path | None = None
    state_path: Path | None = None
    target: str | None = None
    detach: bool = False
    opener: str | None = None
```

Similar request types should exist for:

- `RestartRequest`
- `StopRequest`
- `OpenRequest`
- `SyncRequest`

Required result:

```python
@dataclass(frozen=True)
class ActionResult:
    ok: bool
    code: str
    message: str
    exit_code: int = 0
    changed_targets: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
```

Rules:

- CLI and Web UI both call these use cases.
- Use cases own calls to runtime functions and state persistence.
- Presentation code must not call runtime mutation helpers directly.
- Message wording can be adapted at the edge, but action semantics must be
  shared.

#### Action Migration Order

Migrate actions in risk order, not command order:

1. `sync`: no opener behavior, validates reconciliation and state update design.
2. `stop`: small target validation surface, no applied-result persistence.
3. `launch` / `restart`: runtime mutation plus applied-result persistence.
4. `open`: highest risk because opener capabilities, terminal runtime behavior,
   workspace files, and project-folder intents all interact.

Low-level action use cases accept already-loaded `workspace`, `plan`, `state`,
and `state_path` so tests and CLI code can exercise exact workflow branches. The
transport-level dispatcher, `execute_workspace_action()`, accepts config/state
paths, loads the workspace once, normalizes public targets, resolves opener
intent, and then delegates to the lower-level use cases. Web UI routes call this
dispatcher rather than rebuilding those decisions locally.

Action use cases return data, not printed text or HTTP responses. CLI and Web UI
may map the same `ActionResult` into different wording only when the transport
requires it.

### Status And Plan Queries

Status should be built once and consumed by both CLI JSON output and Web UI.

Required result:

```python
@dataclass(frozen=True)
class WorkspaceStatusResult:
    status: str
    project: str | None
    config_path: str
    state_path: str
    slots: tuple[SlotStatus, ...]
    runtime_sync: RuntimeSyncReport | None = None
    error: str | None = None
```

Text rendering remains separate. `format_status()` can survive as a renderer,
but status construction should not be duplicated.

### Config Workflows

Move config behavior out of the HTTP handler:

- project probe
- config load
- config save conflict detection
- config validation before save
- init workspace
- profile and agent list queries where practical

Config save should return:

- success/failure
- stable error code
- current file version on conflict
- diagnostics for valid saved content

Current slice:

- `save_workspace_config()` owns config conflict detection, validation,
  diagnostics, atomic write, and returned file version metadata.
- `read_workspace_config()` owns config editor payload construction for missing,
  needs-init, and ready states.
- `probe_project()` owns project setup state detection.
- `initialize_workspace()` owns environment detection plus starter config/state
  initialization.
- `profile_options()`, `opener_options()`, and `agent_options()` own Web UI
  metadata payload construction.
- Web UI still owns HTTP request parsing and response status-code mapping.
- The remaining config-layer work is deeper validation issue collection rather
  than transport extraction.

### Diagnostics

Split doctor into:

```python
def collect_doctor_report(workspace: WorkspaceConfig, plan: WorkspacePlan) -> DoctorReport
def render_doctor_report(report: DoctorReport) -> str
```

During migration, keep `build_doctor_report()` as a compatibility wrapper that
returns text, but make new application code call `collect_doctor_report()`.

## Runtime Boundary

Extend the existing `Backend` protocol instead of creating a second competing
runtime protocol.

Required addition:

```python
class Backend(Protocol):
    def list_windows(self, session: str) -> set[str]: ...
```

Rules:

- Direct `subprocess.run(["tmux", ...])` calls are allowed only in backend
  implementation modules.
- `runtime_sync.py`, `sessions.py`, and `webui/server/` must use the backend
  for runtime inspection.
- Tests should use fake backends instead of patching subprocess calls where
  possible.

## State Boundary

Keep `StateRepository` and the current `load_state()` / `save_state()` functions
for compatibility, but add an application-level state update boundary.

Initial API:

```python
class StateStore:
    def load(self) -> WorkspaceState: ...
    def save(self, state: WorkspaceState) -> None: ...
    def update(self, fn: Callable[[WorkspaceState], WorkspaceState]) -> WorkspaceState: ...
```

Rules:

- Workflow use cases call `StateStore.update()` for applied runtime metadata.
- Presentation code should not call `save_state()` for workflow side effects.
- File locking is not required in the first implementation, but the API must not
  prevent adding it later.

## Validation Direction

Add validation in layers rather than putting every rule into dataclass
constructors.

Minimum validation issues:

- unknown top-level, slot, window, agent, and opener fields
- invalid `runtime`
- invalid `resume_mode`, `create_mode`, and `label_mode`
- duplicate slot names
- duplicate window names within a slot
- invalid env var names
- non-string `cwd`, `command`, `agent`, and `name`
- missing launch command for windows that have neither `command` nor `agent`

Compatibility plan:

- Phase 1: return unknown fields as warnings. Implemented for top-level,
  display, agent, opener, slot, and window mappings.
- Phase 2: document warnings in CLI and Web UI.
- Future major version: promote unknown fields to errors if desired.

Current validation coverage:

- Unknown fields are collected as structured warning `Issue`s.
- Invalid `runtime`, `resume_mode`, `create_mode`, and `label_mode` values are
  collected as structured error `Issue`s.
- Non-string scalar fields, duplicate slot/window names, invalid env keys, and
  missing launch commands are collected as structured error `Issue`s.
- `read_workspace_config()` and `save_workspace_config()` both return validation
  issues, and the Web config editor renders those issues for both existing files
  and failed save attempts.
- `save_workspace_config()` rejects validation errors before normalization,
  planning, or writing.
- Remaining work: surface validation warnings/errors in richer CLI/Web UI views
  instead of only returning them in config API payloads.

## API Contract

### Doctor

Target HTTP response:

```json
{
  "status": "ready",
  "report": {
    "project": "project",
    "issues": [
      {
        "issue_type": "missing_command",
        "severity": "error",
        "message": "Command not found: codex",
        "target": "dev.planner",
        "context": {"command": "codex"},
        "fixable": false
      }
    ]
  },
  "text": "doctor: project\n..."
}
```

The `text` field remains temporarily for compatibility. Frontend code should
prefer `report.issues` once available.

### Actions

Target HTTP success response:

```json
{
  "success": true,
  "code": "workspace_launched",
  "message": "Launched workspace",
  "changed_targets": ["dev:planner"],
  "warnings": []
}
```

Target HTTP error response:

```json
{
  "success": false,
  "code": "target_not_found",
  "error": "Cannot launch target: dev:missing",
  "changed_targets": [],
  "warnings": []
}
```

HTTP status codes are transport mapping, not application semantics:

- validation or target errors: 400
- missing config/project: 404
- config conflict: 409
- unexpected errors: 500

## Architecture Rules

Add tests or static checks for these rules:

- `cc_branch.webui` must not import runtime mutation helpers such as
  `ensure_slot`, `apply_workspace`, `restart_workspace`, or `stop_workspace`.
- `cc_branch.cli` must not call `save_state()` for workflow side effects after
  the application state boundary exists.
- Direct tmux subprocess calls must be isolated to backend implementation files.
- Doctor collection returns `DoctorReport`; text rendering is a separate call.
- Application modules must not import `argparse`, `BaseHTTPRequestHandler`, or
  `rich`.

## Implementation Plan

Each phase should be independently reviewable. Do not combine broad file moves
with behavior migration in the same PR. A phase is complete only when the old
surface-specific path is either removed or explicitly marked as a temporary
compatibility wrapper.

### Phase 0: Baseline Behavior Tests

Before extraction, add characterization tests for the workflows most likely to
drift:

- CLI `start --detach`
- CLI/Web UI launch target
- CLI/Web UI restart target
- CLI/Web UI open workspace with layout-capable opener
- sync changed/missing/untracked target
- doctor JSON/text compatibility
- config save conflict

These tests should describe current behavior, not ideal behavior.

### Phase 1: Structured Diagnostics

- Add `collect_doctor_report() -> DoctorReport`.
- Add `render_doctor_report(report) -> str`.
- Keep `build_doctor_report()` as a text-returning compatibility wrapper.
- Update Web UI doctor endpoint to include structured report and text.

### Phase 2: Shared Status Builder

- Add `application/workspace_status.py`.
- Move status payload construction out of CLI and Web UI.
- Keep existing CLI text output and Web UI response shape compatible.

### Phase 3: Runtime Inspection Boundary

- Add `Backend.list_windows()`.
- Replace direct tmux inspection in runtime sync, sessions, and Web UI status.
- Add the architecture check for direct tmux subprocess usage.

### Phase 4: Workspace Action Use Cases

- Add shared use cases for launch, restart, stop, sync, and open.
- Migrate CLI first because it has simpler transport concerns. CLI migration now
  includes launch, foreground start, attach, dashboard, restart, stop, open,
  sync, doctor diagnostics, and init file creation.
- Migrate Web UI after CLI behavior is covered by use-case tests. Web UI action
  dispatch is now migrated to the shared application action dispatcher.
- Remove duplicated action helpers from `webui/server/` once routes call the
  shared use cases.
- Do not migrate CLI and Web UI actions in the same PR unless the diff is small
  enough to review as one coherent change.

### Phase 5: State Update Boundary

- Add `StateStore.update()`.
- Move applied-result state persistence into application use cases.
- Keep legacy state functions as wrappers for external compatibility.

### Phase 6: Config Workflows And Validation

- Move project probe, config load, config save, init, and save conflict detection
  into application config workflows. Project probe, config read, config save,
  init, metadata queries, environment inspection, minimal init, and save conflict
  detection are complete.
- Add validation issue collection. Unknown field, enum, duplicate name, type,
  env-key, and missing launch-command rules are complete.
- Surface validation warnings/errors through CLI and Web UI. Web config editor
  issue display is complete; CLI validation display remains a future UX polish
  item because saves currently happen through Web/API workflows.

### Phase 7: Cleanup And Documentation

- Remove dead helpers from CLI and Web UI.
- Update `docs/architecture.md` to describe the real shipped architecture.
- Add a short contributor guide section explaining where new workflow behavior
  belongs.

## Acceptance Criteria

- Existing test suite passes: `python -m unittest discover tests`.
- Existing public Python APIs remain import-compatible unless a deprecation note
  and migration path are included.
- CLI and Web UI share the same implementation for launch, restart, stop, open,
  and sync.
- `webui/server/` contains HTTP and serialization code, not workspace workflow
  decisions.
- `cli.py` contains argparse, service calls, exit-code mapping, and rendering,
  not runtime orchestration.
- Runtime inspection and mutation go through `Backend`.
- Doctor has structured and rendered outputs.
- Config validation reports invalid enum values and unknown fields before
  runtime execution.
- State mutation for applied runtime results happens through an application
  boundary.
- Architecture tests prevent presentation layers from reintroducing direct
  runtime/state coupling.

## Explicit Tradeoffs

- This keeps some existing modules in place longer than a clean-room layered
  design would. That is intentional: behavior preservation matters more than
  directory purity.
- Service/use-case extraction may temporarily increase indirection. The payoff is
  reached only when both CLI and Web UI call the shared use cases.
- Unknown config fields start as warnings to avoid surprising existing users.

## Risks And Mitigations

- Risk: A large mechanical refactor breaks CLI behavior.
  Mitigation: baseline characterization tests before moving workflows.

- Risk: New abstraction becomes too generic.
  Mitigation: introduce ports only when at least two callers need the same
  boundary or when tests require a fake.

- Risk: Web UI response compatibility breaks.
  Mitigation: include old fields during transition and add new structured fields
  alongside them.

- Risk: Tests keep patching old module-level functions and hide boundary leaks.
  Mitigation: add fake backend/state store tests and architecture checks.

## Recommended PR Sequence

1. Add baseline workflow tests.
2. Split doctor collection from rendering.
3. Add shared status builder.
4. Add backend `list_windows()` and remove direct tmux inspection.
5. Add workspace action use cases and migrate CLI.
6. Add `execute_workspace_action()` and migrate Web UI actions to the shared
   dispatcher.
7. Add state update boundary.
8. Move config workflows and conflict detection into application code.
9. Add validation issue collection.
10. Add architecture tests for presentation/runtime/state boundaries.
11. Remove duplicated helpers and update architecture docs.

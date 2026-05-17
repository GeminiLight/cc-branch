# Package Architecture Spec

## Decision

`cc_branch/` root should not be the default home for implementation modules.
Root-level files are allowed only when they are:

- CLI or process entrypoints
- stable public API facades
- small cross-cutting constants or exceptions
- temporary compatibility wrappers during a package migration

Subsystem implementation belongs in package directories with clear ownership.

## Target Shape

```text
cc_branch/
  __init__.py          public Python API facade
  __main__.py          python -m entrypoint
  cli/                CLI presentation package
  constants.py        small shared constants
  exceptions.py       shared exception types

  application/        use cases shared by CLI, Web UI, and Python callers
  doctor/             diagnostics and safe auto-fix
  models/             typed config, plan, state, opener, and diagnostic models
  planner/            config/state to executable plan resolution
  runtime/            runtime capabilities, execution, sync, backend adapters
  openers/            local app/editor/terminal openers
  webui/server/       HTTP transport and static asset serving
```

Compatibility facades may remain at the root, but new internal imports should
target the owning package module. For example, use
`cc_branch.runtime.sync` rather than `cc_branch.runtime_sync` in new code.

## Implemented Runtime Package

```text
cc_branch/runtime/
  __init__.py      compatibility facade for `cc_branch.runtime`
  execution/       apply/restart/stop/attach/dashboard/status execution
  backends.py      Backend protocol and TmuxBackend implementation
  capabilities.py slot runtime capability model
  sync/            runtime/config synchronization reports
  sessions.py      session list/inspect/prune/restore operations
  shells.py        platform-aware shell helpers
```

The former root modules `backends.py`, `runtime_capabilities.py`,
`runtime_sync.py`, `sessions.py`, and `shells.py` now exist only as thin
compatibility facades.

## Import Rules

- Application code may depend on `runtime.capabilities`, `runtime.sync`, and
  `runtime.execution` APIs.
- Runtime code must not import CLI or Web UI modules.
- Presentation layers may import application use cases and public runtime status
  helpers, but should not own runtime orchestration policy.
- Tests should patch owner modules, not root compatibility facades, unless the
  test is explicitly about public import compatibility.

## Implemented Packages

- `cc_branch/application/`
- `cc_branch/adapters/`
- `cc_branch/agent_registry/`
- `cc_branch/bootstrap/`
- `cc_branch/cli/`
- `cc_branch/config/`
- `cc_branch/doctor/`
- `cc_branch/models/`
- `cc_branch/openers/`
- `cc_branch/planner/`
- `cc_branch/profiles/`
- `cc_branch/repository/`
- `cc_branch/runtime/`
- `cc_branch/webui/server/`

## Next Candidates

1. `cc_branch/cli/__init__.py`: split command handlers further once the public
   command dispatch facade becomes the next bottleneck.
2. `cc_branch/state.py`: consider a `state/` package only if merge semantics
   grow beyond the current small public API.
3. `cc_branch/context.py`: keep as a single boundary object unless it starts
   owning workflows instead of loading config/state/plan.

These should be migrated one subsystem at a time with compatibility facades and
full test coverage after each step.

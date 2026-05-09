# Module-to-Package Refactor Status

## Decision Rule

Convert a module into a package when the split improves ownership boundaries,
not just because the file is long. Good candidates have multiple independent
responsibilities, hidden private subsystems, or sit on a layer boundary where
future behavior would otherwise add more central branching.

Keep modules flat when they are cohesive leaf helpers, compatibility shims, or
small boundary objects.

## Completed Package Conversions

- `cc_branch/openers/`: local opener metadata, adapters, and command launching.
- `cc_branch/application/workspace_actions/`: target parsing, command specs,
  lifecycle actions, opener policy, sync, and action dispatch.
- `cc_branch/application/config_workflows/`: config read/save/probe/init,
  profile/opener/agent metadata, conflict detection, and validation-before-write.
- `cc_branch/application/config_validation/`: raw schema constants, Issue
  factories, shared validators, section validators, and YAML collection.
- `cc_branch/webui/server/`: HTTP handler, auth, static files, terminal
  compatibility helpers, and server startup.
- `cc_branch/runtime/`: execution facade, backend protocol, capability model,
  sync facade, sessions, and shell helpers.
- `cc_branch/runtime/execution/`: backend ops, target resolution, window
  creation, lifecycle, dashboard, and status rendering.
- `cc_branch/runtime/sync/`: sync models, launch fingerprints, runtime
  inspection, report construction, state recording, and target selection.
- `cc_branch/cli/`: parser, help rendering, CLI constants, and command dispatch
  facade.
- `cc_branch/models/`: config, plan, state, doctor, opener, and shared model
  groups.
- `cc_branch/doctor/`: report collection, rendering, messages, and safe
  autofix.
- `cc_branch/planner/`: command building, naming, paths, slots, and workspace
  planning.
- `cc_branch/bootstrap/`: environment probing, config generation, session
  bootstrapping, first-run file writes, and result models.
- `cc_branch/agent_registry/`: registry model, source paths, YAML IO, layered
  merge loading, and built-in cache.
- `cc_branch/adapters/`: adapter interface, no-op adapter, resume strategies,
  and adapter selection.
- `cc_branch/profiles/`: profile definitions, catalog queries, and YAML
  rendering.
- `cc_branch/config/`: config paths, raw YAML loading, normalization, and
  starter config initialization.
- `cc_branch/repository/`: state YAML codec, repository validation, and atomic
  persistence.

Each conversion preserves the old public import path through a package
`__init__.py` facade and has an architecture guard in
`tests/test_application_architecture.py`.

## Current Root Policy

Root-level Python files should now be one of:

- import compatibility facades such as `backends.py`, `sessions.py`, and
  `runtime_sync.py`
- entrypoints such as `__main__.py`
- small cohesive boundary objects such as `context.py`
- simple leaf helpers such as `targets.py`, `templates.py`, and
  `desktop_backend.py`

New multi-responsibility code should be added inside the owning package, not as
a new large root module.

## Remaining Watch List

- `cc_branch/webui/server/handler.py`: keep watching route growth. New API
  endpoint policy should go in `webui/server/api.py`, not in handler methods.
- `cc_branch/state.py`: keep flat while it remains a three-function public API;
  move merge semantics into a `state/` package if merge policy grows.
- `cc_branch/context.py`: keep as a small load boundary unless it starts owning
  workflows that belong in `application/`.

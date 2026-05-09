# Contributing to cc-branch

Thanks for contributing to cc-branch.

## Source of truth

The current project is no longer just a small dict-based CLI. The main implementation surface now includes:

- `cc_branch/cli/` — CLI parser, help rendering, and command dispatch facade
- `cc_branch/application/` — shared workflow use cases for CLI, Web UI, and Python callers
- `cc_branch/models/` — typed config / plan / state / doctor models
- `cc_branch/config/` — workspace config path resolution, loading, normalization, and initialization
- `cc_branch/context.py` — shared config → state → plan loading pipeline
- `cc_branch/planner/` — typed plan resolution
- `cc_branch/adapters/` — agent-specific create/resume behavior
- `cc_branch/agent_registry/` — layered built-in, user, workspace, and project agent definitions
- `cc_branch/runtime/` — runtime capabilities, managed backends, execution, sync, shell helpers, and session lifecycle
- `cc_branch/state.py` + `cc_branch/repository/` — typed state loading and atomic persistence
- `cc_branch/bootstrap/` + `cc_branch/profiles/` — first-run setup and starter workspace profiles
- `cc_branch/doctor/` — diagnostics and safe auto-fix
- `cc_branch/webui/server/` — Web UI backend and packaged asset host

If you change user-visible behavior, update docs in the same PR.

## Development setup

### Requirements

- Python 3.10+
- `tmux`
- Git

### Install for development

```bash
pip install -e .
```

Editable installs do not trigger the frontend build. If you need the web UI
assets to be present for local testing of `cc-branch serve`, run:

```bash
python scripts/build-webui.py
```

If you are validating a clean environment, use a venv.

## Running tests

### Main test suite

```bash
python3 -m unittest discover tests
```

### Multi-version validation

```bash
python3.10 -m venv .venv310
. .venv310/bin/activate
pip install -e .
python -m unittest discover tests
deactivate
```

### Useful focused runs

```bash
python3 -m unittest tests.test_cli
python3 -m unittest tests.test_workspace
python3 -m unittest tests.test_webui
```

## Running locally

```bash
./bin/cc-branch --help
./bin/cc-branch plan --write-state
./bin/cc-branch session list
./bin/cc-branch serve
```

## Project layout

```text
cc_branch/
  cli/
  models/
  config/
  context.py
  planner/
  adapters/
  agent_registry/
  runtime/
  state.py
  repository/
  doctor/
  bootstrap/
  profiles/
  webui/

docs/
wiki/
tests/
examples/
```

## Adding a new agent

Agent definitions live in `cc_branch/agents.yaml`. To add a built-in agent:

1. Add an entry to `cc_branch/agents.yaml` with at least:
   - `command` — the executable name
   - `install_hint` — shown by `doctor` when the CLI is missing
   - `resume_mode` — `flag`, `internal`, or `none`
   - `resume_template` — template string using `{session_id}` etc.

2. If the agent should appear in profile templates, update `PROFILES` in `cc_branch/profiles/definitions.py` (add the agent name to `preferred_agents` lists).

3. Run tests to make sure `doctor`, `init`, and `plan` still work.

For user-local agents, add or override entries in `~/.cc-branch/agents.yaml` or `.cc-branch/agents.yaml`. Overrides are field-level merges, so changing `command` does not require copying the built-in `resume_template`.

## Contribution guidelines

- Prefer typed models over ad-hoc dicts in core logic
- Put new user-facing workflow behavior in `cc_branch/application/`
- Keep `cli/` focused on argparse, exit-code mapping, and terminal rendering
- Keep `webui/server/` focused on HTTP routing, auth, JSON serialization, and static assets
- Keep planner and runtime behavior covered by tests
- Add tests for new user-visible CLI or Web UI behavior
- Keep comments concise and useful
- Preserve cross-platform assumptions: macOS, Linux, Windows-with-tmux environment
- Be explicit about shipped vs proposed behavior in docs

## Workflow Boundaries

Use this rule of thumb when deciding where code belongs:

- `cc_branch/application/workspace_actions/`: start, launch, restart, stop,
  open, attach, dashboard, sync, and applied runtime-state persistence.
- `cc_branch/application/workspace_status.py`: status payload construction,
  including missing, needs-init, ready, and invalid-config states.
- `cc_branch/application/config_workflows/`: config read/save/probe/init,
  profile/opener/agent metadata, conflict detection, and validation-before-write.
- `cc_branch/application/config_validation/`: raw config structural validation
  before normalization or planning.
- `cc_branch/application/diagnostics.py`: structured doctor reports and text
  rendering.
- `cc_branch/cli/`: parse args, call application use cases, render output.
- `cc_branch/webui/server/`: map HTTP requests/responses to application
  payloads.

If a behavior must be identical in CLI and Web UI, it should not live in either
presentation file.

## Documentation expectations

When behavior changes, keep these aligned:

- `README.md`
- `README.zh.md`
- `docs/getting-started.md`
- `docs/quickstart.md`
- `docs/user-guide.md`
- `docs/features.md`
- `docs/architecture.md`
- `docs/webui-spec.md`
- `wiki/README.md`

If a design note is historical, mark it as such instead of leaving it to imply current behavior.

## Typical workflow

1. Create a branch
2. Make the code change
3. Add or update tests
4. Update docs/wiki
5. Run the relevant test suite
6. Open a PR with clear scope and rollout notes

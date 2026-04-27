# Contributing to cc-branch

Thanks for contributing to cc-branch.

## Source of truth

The current project is no longer just a small dict-based CLI. The main implementation surface now includes:

- `cc_branch/cli.py` — CLI entrypoint and command routing
- `cc_branch/models.py` — typed config / plan / state / doctor models
- `cc_branch/context.py` — shared config → state → plan loading pipeline
- `cc_branch/planner.py` — typed plan resolution
- `cc_branch/adapters.py` — agent-specific create/resume behavior
- `cc_branch/runtime.py` — tmux runtime operations
- `cc_branch/state.py` + `cc_branch/repository.py` — typed state loading and atomic persistence
- `cc_branch/sessions.py` — session lifecycle operations
- `cc_branch/doctor.py` — diagnostics and safe auto-fix
- `cc_branch/webui/server.py` — Web UI backend and packaged asset host

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
  cli.py
  models.py
  context.py
  planner.py
  adapters.py
  runtime.py
  state.py
  repository.py
  sessions.py
  doctor.py
  bootstrap.py
  profiles.py
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

2. If the agent should appear in profile templates, update `PROFILES` in `cc_branch/profiles.py` (add the agent name to `preferred_agents` lists).

3. Run tests to make sure `doctor`, `init`, and `plan` still work.

For user-local agents (no source change needed), see `README.md` → "Adding custom agents".

## Contribution guidelines

- Prefer typed models over ad-hoc dicts in core logic
- Keep planner and runtime behavior covered by tests
- Add tests for new user-visible CLI or Web UI behavior
- Keep comments concise and useful
- Preserve cross-platform assumptions: macOS, Linux, Windows-with-tmux environment
- Be explicit about shipped vs proposed behavior in docs

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

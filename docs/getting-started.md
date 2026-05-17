# Getting Started with CC Branch

CC Branch is a CLI-first workspace orchestrator for terminal AI workflows. It helps you turn a project-local config file into a repeatable workspace, then get back to it with less manual setup.

## What you need

- The agent CLIs you want to reference in `.cc-branch/config.yaml`
- Python 3.10+ only when installing from PyPI or source
- `tmux` only if you want reusable `layoutBackend: tmux` tabs

## Install

### Homebrew

Recommended for macOS and Linux after the tap is published:

```bash
brew install GeminiLight/cc-branch/cc-branch
```

The Homebrew formula installs Python dependencies inside Homebrew's managed environment, so users do not need to prepare their own Python environment first.

### Desktop app

Download the latest desktop build for your platform from [GitHub Releases](https://github.com/GeminiLight/cc-branch/releases).

### Python users

```bash
pipx install cc-branch
```

Use `pip install cc-branch` only inside a virtual environment. Prefer `pipx` for day-to-day CLI usage.

### From source

```bash
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
pip install .
# CLI-only source install without building the Web UI:
# CC_BRANCH_SKIP_WEBUI_BUILD=1 pip install .
```

Source installs build the bundled Web UI from `apps/web`, so they need Node.js/npm unless `CC_BRANCH_SKIP_WEBUI_BUILD=1` is set. The skip mode installs the CLI only; `cc-branch serve` will report that Web UI assets are missing until you build them with `python scripts/build-webui.py` and reinstall. Published wheel/sdist installs from PyPI already include the Web UI assets and do not require Node.js/npm.

For common failures, see `docs/install-troubleshooting.md`.

## Check the CLI

```bash
cc-branch --help
ccb --help
```

## Create your first workspace

### 1. Start inside a project

```bash
cd /path/to/your/project
cc-branch init
```

During `init`, CC Branch typically:

- checks which layout backends are available
- detects supported agent CLIs on `PATH`
- generates a starter config from the default `development` profile
- writes `.cc-branch/state.yaml`
- bootstraps `session_id` values when needed
- updates `.gitignore` for local state

Use `--profile design` for product/design work or `--profile minimal` for a single-pane workspace.

### 2. Know the two files it creates

- `.cc-branch/config.yaml` — project config you can commit
- `.cc-branch/state.yaml` — machine-local runtime state

### 3. Preview the resolved plan

```bash
cc-branch plan
```

This is the moment to confirm:

- which tabs and panes will be created
- which commands each pane will run
- which `session_id` values will be reused or created
- which labels and post-launch commands will be applied

### 4. Launch the workspace

```bash
cc-branch start
```

`start` creates the configured tmux sessions or direct local processes and attaches to the first reusable tab. Use `cc-branch start --detach` only when you want reusable tmux sessions created without attaching or opening direct-layout processes.

Use `cc-branch dashboard` or `cc-branch start --dashboard` when you want the tiled dashboard. `start` itself does not silently switch into dashboard mode based on config.

Use `cc-branch open` when you want CC Branch to open the visible workspace in your chosen local app:

```bash
cc-branch open --opener warp
cc-branch open --opener vscode
cc-branch open dev:planner --opener cursor
```

### 5. Work with it day to day

```bash
cc-branch status
cc-branch attach dev
cc-branch attach dev:planner
cc-branch doctor --fix
cc-branch session list
```

### 6. Open the Web UI

```bash
cc-branch serve
```

By default, it starts on `http://127.0.0.1:8080`.

You can also run `cc-branch serve` before `cc-branch init`; the Web UI will show a setup flow and create the config after you choose a starter profile.

In the Web UI, choose one tool and then use either "Open workspace" or "Open project directory". Workspace open adapts to the tool: Terminal runs dashboard or attach commands, Warp uses stable Launch Configurations for layouts, and VS Code/Cursor open the real project folder and install folder-open tasks through `.vscode/tasks.json` to create integrated terminals. Project directory open always uses the system file manager so the user lands in a normal folder view. Tmux-backed tabs are reusable, so opening from another Terminal, Warp, VS Code, or Cursor window attaches to the same sessions. Direct-layout panes are external processes and are not reusable. "Start in background" creates tmux sessions and opens direct-layout panes when the selected opener supports command execution.

If you bind it to a non-loopback host, use `--token` or `CC_BRANCH_WEB_TOKEN`.
When a token is configured, open the printed `/?token=...` URL once to establish the browser cookie.

## Built-in profiles

| Profile | Best for |
| --- | --- |
| `development` | One development tab with frontend, backend, algorithm, and docs panes |
| `design` | Product discussion and implementation, plus a separate design tab |
| `minimal` | One tab with one agent pane |

Starter profiles keep `.cc-branch/config.yaml` focused on workspace structure. Built-in agent profiles are available automatically, so generated configs reference `agent: codex` or `agent: claude` without copying the full agent definition into every project.

## Minimal init mode

If you only want the files and do not need the guided bootstrap flow:

```bash
cc-branch init --minimal
```

## Next reads

- `docs/quickstart.md`
- `docs/install-troubleshooting.md`
- `docs/user-guide.md`
- `docs/features.md`
- `docs/architecture.md`
- `docs/webui-spec.md`

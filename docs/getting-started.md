# Getting Started with CC Branch

CC Branch is a CLI-first workspace orchestrator for terminal AI workflows. It helps you turn a project-local config file into a repeatable workspace, then get back to it with less manual setup.

## What you need

- `tmux`
- The agent CLIs you want to reference in `.cc-branch.yaml`
- Python 3.10+ only when installing from PyPI or source
- On Windows, a `tmux`-capable environment such as WSL, MSYS2, or Cygwin

## Install

### Homebrew

Recommended for macOS and Linux once the tap is published:

```bash
brew install GeminiLight/cc-branch/cc-branch
```

The Homebrew formula installs Python dependencies inside Homebrew's managed environment, so users do not need to prepare their own Python environment first.

### Desktop app

Download the latest `.dmg`, `.msi`, or `.AppImage` from [GitHub Releases](https://github.com/GeminiLight/cc-branch/releases).

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
# Skip the Web UI build if you do not need it:
# CC_BRANCH_SKIP_WEBUI_BUILD=1 pip install .
```

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

- checks `tmux`
- detects supported agent CLIs on `PATH`
- generates a starter config from the default `solo-dev` profile
- writes `.cc-branch.state.yaml`
- bootstraps `session_id` values when needed
- updates `.gitignore` for local state

Use `--profile ai-pair` or `--profile minimal` only when you want a non-default template.

### 2. Know the two files it creates

- `.cc-branch.yaml` — project config you can commit
- `.cc-branch.state.yaml` — machine-local runtime state

### 3. Preview the resolved plan

```bash
cc-branch plan
```

This is the moment to confirm:

- which tmux sessions will be created
- which commands each window will run
- which `session_id` values will be reused or created
- which labels and post-launch commands will be applied

### 4. Launch the workspace

```bash
cc-branch start
```

`start` creates the configured tmux sessions and attaches to the first slot. Use `cc-branch start --detach` only when you want reusable tmux sessions created without attaching or opening terminal-runtime slots.

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

In the Web UI, choose one tool and then use either "Open workspace" or "Open project directory". Workspace open adapts to the tool: Terminal/iTerm2 run dashboard or attach commands, Warp uses Launch Configurations for layouts, and VS Code/Cursor open a generated `.code-workspace`. Project directory opens start an interactive shell in terminal apps and open the folder in editor apps. In VS Code/Cursor, each tmux slot becomes one attach task, so tmux windows are not expanded into separate integrated terminals; plain `runtime: terminal` slots become visible shell tasks. Tmux workspaces are reusable, so opening from another Terminal, Warp, or iTerm2 window attaches to the same sessions. Plain `runtime: terminal` slots are external processes and are not reusable. "Start in background" only creates tmux sessions and does not open a visible terminal window.

If you bind it to a non-loopback host, use `--token` or `CC_BRANCH_WEB_TOKEN`.
When a token is configured, open the printed `/?token=...` URL once to establish the browser cookie.

## Built-in profiles

| Profile | Best for |
| --- | --- |
| `solo-dev` | One developer with planner, builder, review, and scratch windows |
| `ai-pair` | A coder and reviewer workflow |
| `minimal` | A very small setup with one main agent window |

Starter profiles keep `.cc-branch.yaml` focused on workspace structure. Built-in agent profiles are available automatically, so generated configs reference `agent: codex` or `agent: claude` without copying the full agent definition into every project.

## Minimal init mode

If you only want the files and do not need the guided bootstrap flow:

```bash
cc-branch init --minimal
```

## Next reads

- `docs/quickstart.md`
- `docs/user-guide.md`
- `docs/features.md`
- `docs/architecture.md`
- `docs/webui-spec.md`

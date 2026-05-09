# CC Branch

[English](README.md) | [中文](README.zh.md)

> Start and resume multiple Agent CLI and shell windows from one project config.

CC Branch (`cc-branch`, `ccb`) is a local workspace manager for developers who run several AI coding agents in one repository. It records the window layout, agent commands, working directories, and local session metadata so the same working setup can be recreated quickly.

## Use Cases

- Run planner, coder, reviewer, dev server, and shell windows as one repeatable project workspace.
- Resume the same AI coding setup across days without manually rebuilding windows.
- Share a project workspace template with teammates while keeping local session state private.

## Key Features

- **Workspace templates** for common solo, pair, and minimal AI coding workflows.
- **Start and reconnect commands** to preview, launch, attach, stop, and restart windows.
- **Session continuity** for Agent CLIs that support resuming previous sessions.
- **Local dashboard and health checks** for setup, status, config editing, and common actions.

## Install

Requirements: `tmux`, the Agent CLIs used by your config, and Python 3.11+ when installing through PyPI or source. Windows users need WSL, MSYS2, or Cygwin.

```bash
pipx install cc-branch
```

Or install from source:

```bash
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
pip install .
```

## Quick Start

The shortest path is to start the Web UI in your project:

```bash
cd /path/to/project
cc-branch serve
```

Default address: `http://127.0.0.1:8080`. If the project is not configured yet, the Web UI will guide you through creating `.cc-branch/config.yaml`.

If you prefer the terminal flow:

```bash
cc-branch init    # create .cc-branch/config.yaml and local state
cc-branch start   # start the tmux workspace and enter it
```

Use `cc-branch open` when you want CC Branch to open the workspace through your configured local app. For example, `cc-branch open --opener warp` or `cc-branch open --opener vscode`.

Use `cc-branch start --detach` only when you want to create reusable tmux sessions without attaching or opening terminal-runtime slots.

Optional checks:

- `cc-branch plan` previews what will be launched before starting anything.
- `cc-branch doctor` checks common environment/config issues.

In the Web UI, choose one local tool and then use either "Open workspace" or "Open project directory". CC Branch adapts the action for terminals, Warp, VS Code, and Cursor. Project directory opens start an interactive shell in terminal apps and open the folder in editor apps. Use the background start action only when you want tmux sessions created without a visible terminal.

## Example Config

```yaml
version: 1
project: "my-app"
root: "."

slots:
  - name: "dev"
    windows:
      - name: "planner"
        agent: "codex"
      - name: "server"
        command: "npm run dev"
```

Built-in agent profiles such as `codex`, `claude`, `gemini`, `cursor`, and `kimi` are available by default. Add an `agents` section only when you want to override a profile or define a custom local agent.

## More

Project config is stored in `.cc-branch/config.yaml`; local runtime state is stored in `.cc-branch/state.yaml` and is usually not committed. For more detail, see `docs/getting-started.md`, `docs/user-guide.md`, and `docs/features.md`.

## License

MIT License. See [LICENSE](LICENSE) for details.

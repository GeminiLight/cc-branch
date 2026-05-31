<div align="center">

# CC Branch

### Restore your multi-agent CLI workbench in one command

English | [中文](README.zh.md)

[![CI](https://github.com/GeminiLight/cc-branch/actions/workflows/ci.yml/badge.svg)](https://github.com/GeminiLight/cc-branch/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-v1.0.0-green)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

CC Branch restores the working environment around a project: agents, terminals, editors, local folders, SSH machines, and reusable sessions.

## Why Developers Use It

### 1. Restore the full project workbench

- A project may need Codex, Claude Code, dev servers, logs, editors, and multiple tmux windows.
- CC Branch lets you configure that workbench once, then bring it back with one command.

### 2. Continue from existing sessions

- Agent and tmux sessions may already be running from the last time you worked on the project.
- CC Branch attaches back to those sessions, so returning to a project feels like continuing work instead of starting over.

### 3. Work across local and SSH machines

- A project may span a local repo, SSH machine, GPU box, remote tmux session, and local editor.
- CC Branch keeps local and remote work in one workspace, so returning to the project means continuing instead of rebuilding.

## Install

### Desktop app

Download the desktop app from the [latest GitHub Release](https://github.com/GeminiLight/cc-branch/releases/latest).

Use this when you want the native desktop experience.

### CLI and Web UI with pip

Install the CLI/backend and packaged browser Web UI:

```bash
pip install cc-branch
```

The pip package does not install the desktop app. Use GitHub Releases for the native desktop build.

### From source

Use the source install when you want to develop or inspect the repo locally:

```bash
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
pip install .
```

Source checkouts do not build the Web UI automatically. Run `python scripts/build-webui.py` before `cc-branch serve` when developing the browser UI.

`cc-branch` is also available as `ccb`.

## Quick Use

Start the browser Web UI:

```bash
cc-branch service start
```

It runs at `http://127.0.0.1:8080` by default.

Create and restore a workspace from a project:

```bash
cd /path/to/project
cc-branch init
cc-branch plan
cc-branch start
```

## Daily Commands

| Command | What it is for |
| --- | --- |
| `cc-branch service start` | Start the local Web UI service in the background |
| `cc-branch serve` | Run the Web UI server in the foreground |
| `cc-branch init` | Create a starter `.cc-branch/config.yaml` |
| `cc-branch plan` | Show the agents, commands, panes, openers, and SSH targets before launch |
| `cc-branch start` | Start missing targets or reconnect reusable tmux-backed sessions |
| `cc-branch attach [tab[:pane]]` | Jump into a running tab, pane, or tmux target |
| `cc-branch open --opener <tool>` | Open the project with VS Code, Cursor, Warp, terminal, Web UI, or desktop |
| `cc-branch status` | Show runtime status |
| `cc-branch sync` | Apply config changes to running tmux targets |
| `cc-branch doctor --fix` | Diagnose and repair low-risk environment, config, or state issues |
| `cc-branch session list` | List known agent session metadata |

## Example Config

```yaml
version: 2
project: my-app
root: .
openWith: cursor
layoutBackend: tmux

tabs:
  - name: agents
    panes:
      - name: planner
        agent: codex
      - name: review
        agent: claude
  - name: remote-lab
    ssh:
      host: gpu-dev
      cwd: /srv/my-app
    panes:
      - name: qa
        command: npm run qa
```

Built-in agent profiles are available automatically. Add an `agents` section only when you need to override a built-in profile or define a custom local tool.

## Documentation

- [Getting Started](docs/getting-started.md)
- [User Guide](docs/user-guide.md)
- [Feature Reference](docs/features.md)
- [SSH Remote Workspaces](docs/ssh-remote-workspaces.md)
- [Install Troubleshooting](docs/install-troubleshooting.md)
- [Publishing Runbook](docs/publishing.md)

## License

MIT License. See [LICENSE](LICENSE) for details.

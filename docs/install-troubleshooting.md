# Installation Troubleshooting

This page covers the install failures users are most likely to hit before the first workspace starts.

## Python version is too old

CC Branch requires Python 3.10 or newer for Python-based installs.

Symptom:

```text
Package 'cc-branch' requires a different Python
```

Fix:

```bash
python3.10 -m pip install --upgrade pipx
python3.10 -m pipx install cc-branch
```

## `pip install` is blocked by the system Python

Some macOS and Linux Python installs reject global package installs with an externally managed environment error.

Fix:

```bash
pipx install cc-branch
```

Use `pip install cc-branch` only inside a virtual environment.

## `cc-branch` is not found after install

The package installed, but the shell cannot see the executable.

Fix:

```bash
pipx ensurepath
```

Then restart the shell and run:

```bash
cc-branch --help
ccb --help
```

## Source install fails because npm is missing

Published PyPI packages already include the Web UI. Source installs from a checkout build `apps/web` during packaging, so they need Node.js/npm by default.

Best user install:

```bash
pipx install cc-branch
```

Developer install with Web UI:

```bash
npm --prefix apps/web install
pip install .
```

CLI-only source install:

```bash
CC_BRANCH_SKIP_WEBUI_BUILD=1 pip install .
```

In CLI-only mode, `cc-branch serve` is unavailable until the Web UI is built and the package is reinstalled:

```bash
python scripts/build-webui.py
pip install .
```

## `cc-branch serve` says Web UI assets are missing

This usually means the package was installed from source with `CC_BRANCH_SKIP_WEBUI_BUILD=1`.

Fix by reinstalling a published package:

```bash
pipx install --force cc-branch
```

Or rebuild from source with Node.js/npm available:

```bash
python scripts/build-webui.py
pip install .
```

## tmux is missing

The Python package does not install tmux. CC Branch can install and run without it. Only `layoutBackend: tmux` tabs need tmux; direct-layout panes can still open normal shell, zsh, bash, or PowerShell processes.

macOS:

```bash
brew install tmux
```

Ubuntu/Debian:

```bash
sudo apt-get install tmux
```

If you do not want tmux, change the affected tab to `layoutBackend: direct` in `.cc-branch/config.yaml`.

## Agent CLI commands are missing

CC Branch starts the commands referenced by `.cc-branch/config.yaml`. If `claude`, `codex`, `gemini`, `cursor`, or another configured tool is not on `PATH`, the related pane cannot start.

Fix:

```bash
cc-branch doctor
```

Install the missing CLI, update your `PATH`, or change the agent profile in `.cc-branch/config.yaml`.

## Homebrew command fails

The Homebrew install command works only after the tap has been published and updated for the current release.

Until then, use:

```bash
pipx install cc-branch
```

## Desktop app starts but cannot launch workspaces

The desktop app bundles the CC Branch backend, but it still depends on the local tools used by your workspace. `layoutBackend: tmux` needs tmux; direct-layout panes need the selected shell; Agent panes need their Agent CLI.

Fix:

```bash
cc-branch doctor
```

If you installed only the desktop app, install the runtime and Agent CLIs used by your config separately.

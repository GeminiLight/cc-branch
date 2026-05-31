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
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
python3.10 -m pip install --upgrade pip
python3.10 -m pip install .
```

## `pip install` is blocked by the system Python

Some macOS and Linux Python installs reject global package installs with an externally managed environment error.

Fix:

```bash
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
python -m venv .venv
. .venv/bin/activate
pip install .
```

Use `pip install .` only inside a virtual environment when installing from source.

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

## Source install and Web UI assets

Official PyPI wheels include the packaged browser Web UI. Source checkouts do not build `apps/web` automatically.

PyPI install:

```bash
pip install cc-branch
```

Source install for development:

```bash
pip install .
```

For source development, build the Web UI in the checkout when you intentionally need `cc-branch serve`:

```bash
python scripts/build-webui.py
```

## `cc-branch serve` says Web UI assets are missing

This usually means the package was installed from a source checkout without built Web UI assets, or an old CLI-only package is still installed.

Fix by reinstalling the PyPI package, installing the desktop app from GitHub Releases, or building the Web UI in a source checkout with Node.js/npm available:

```bash
pip install --upgrade --force-reinstall cc-branch
```

```bash
python scripts/build-webui.py
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
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
pip install .
```

## Desktop app starts but cannot launch workspaces

The desktop app bundles the CC Branch backend, but it still depends on the local tools used by your workspace. `layoutBackend: tmux` needs tmux; direct-layout panes need the selected shell; Agent panes need their Agent CLI.

Fix:

```bash
cc-branch doctor
```

If you installed only the desktop app, install the runtime and Agent CLIs used by your config separately.

## Desktop app says the backend did not start

This means the desktop shell opened, but the local API process did not become ready. Release desktop builds require the bundled backend sidecar and do not rely on Python installed on the user's machine; development builds may use a local Python fallback. The error panel shows the startup reason.

Fix:

1. Click **Retry** once in the desktop app. Retry stops any stale backend process and starts the bundled sidecar again.
2. Click **Copy report** and check that it includes the desktop version, platform, architecture, backend source, config path, and state path. Attach that report when filing an issue.
3. Click **Open GitHub Releases** and reinstall the desktop installer for your platform. Use the platform download table, not the Source code zip/tar.gz assets.
4. If you also installed the Python CLI from source or PyPI, you can check the CLI backend directly:

```bash
cc-branch serve
```

If `cc-branch serve` works but the desktop app still reports a backend startup failure, reinstall the desktop installer for your platform from the GitHub Releases page. The release canary checks that the desktop app reports its `desktop_version`, `desktop_platform`, `desktop_arch`, and bundled `cc-branch-backend` sidecar before a release is published.

## Desktop app says the WebView cannot reach the backend

This means the bundled backend reported ready, but the desktop WebView could not fetch `127.0.0.1:<port>`. The copied report includes the desktop version, platform, architecture, backend source, port, config path, and state path.

1. Click **Retry** once in the desktop app.
2. If it still fails, temporarily disable local proxy, VPN, firewall, or endpoint-security rules that intercept `127.0.0.1`.
3. Click **Copy report** and attach it when filing an issue.

Desktop backend launches intentionally ignore inherited `CC_BRANCH_WEB_TOKEN` in the launcher and the sidecar entry point; a token configured for `cc-branch serve` in your shell should not make the packaged desktop app unusable.

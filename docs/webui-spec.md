# CC Branch Web UI Spec

> Status: this document describes the current shipped Web UI backend/frontend surface, not earlier exploratory mockups.

## 1. Overview

The Web UI is now a real shipped surface of cc-branch.

It consists of:

- `cc-branch serve` in the CLI
- `cc_branch.webui.server` as the Python HTTP backend
- bundled static assets under `cc_branch/webui/static/`

The frontend is served by the Python backend; users do not need a separate Node dev server for normal usage.

## 2. Startup

```bash
cc-branch serve
cc-branch serve --host 127.0.0.1 --port 8080
cc-branch serve --host 0.0.0.0 --token "$CC_BRANCH_WEB_TOKEN"
```

Default behavior:

- binds to `127.0.0.1:8080`
- serves `index.html`
- serves packaged static assets from `cc_branch.webui.static`
- resolves config/state target paths without requiring the config to exist
- reports `needs_init` to the frontend when no workspace config exists yet
- refuses non-loopback binds unless `--token` or `CC_BRANCH_WEB_TOKEN` is provided
- when a token is configured, the root page and all `/api/*` endpoints require authentication
- first browser access uses `/?token=<token>` once; the server then redirects to `/` with an HttpOnly same-origin cookie

## 3. Path resolution

By default, the server uses the config/state paths resolved from the directory where it is started.

It also supports:

- query param `project_path=/abs/path`
- env var `CC_BRANCH_CONFIG`
- env var `CC_BRANCH_STATE`

This is important for desktop wrappers or multi-project frontends.

## 4. Current API surface

### Read APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/status` | Return resolved workspace status, or setup state such as `needs_init` |
| `GET` | `/api/config` | Return config file contents, or an empty draft target when config is missing |
| `GET` | `/api/doctor` | Return doctor report, or setup guidance when config is missing |
| `GET` | `/api/profiles` | Return available starter profiles |
| `GET` | `/api/openers` | Return detected local applications that can open the workspace |
| `GET` | `/api/agents` | Return effective agent profiles from built-in, user, workspace, and project layers |
| `GET` | `/api/info` | Return backend info |
| `GET` | `/api/project/probe` | Probe whether a project path is missing, needs init, invalid, or ready |

### Write APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/init` | Initialize a workspace at the selected project path |
| `POST` | `/api/config` | Save config contents |
| `POST` | `/api/action` | Execute a supported workspace action |

### Query scoping

These APIs can be scoped by `project_path`:

- `/api/status?project_path=/abs/path`
- `/api/config?project_path=/abs/path`
- `/api/doctor?project_path=/abs/path`
- `/api/openers?project_path=/abs/path`
- `/api/agents?project_path=/abs/path`
- `/api/init?project_path=/abs/path`
- `/api/config?project_path=/abs/path`
- `/api/action?project_path=/abs/path`

## 5. Current write-action behavior

### `POST /api/init`

Accepts JSON such as:

```json
{
  "profile": "solo-dev",
  "bootstrap_sessions": true
}
```

Current behavior:

- runs environment detection
- uses built-in profiles
- writes config and state files
- returns summary counts and detected agents

### `POST /api/config`

Accepts:

```json
{
  "content": "...yaml text..."
}
```

Writes the config file to disk.

### Missing-config read behavior

When the selected project directory exists but has no config:

- `/api/status` returns `status: "needs_init"` and empty `slots`
- `/api/config` returns `status: "needs_init"`, empty `content`, and the target config path
- `/api/doctor` returns `status: "needs_init"` and setup guidance

This allows `cc-branch serve` to work as the first command in a new project directory.

### `POST /api/action`

Supported actions:

```json
{
  "action": "open | launch | restart | stop | sync",
  "target": "project-slot-name",
  "opener": "auto-terminal",
  "intent": "workspace_dashboard | attach_target | project_folder"
}
```

`target` is optional for workspace-level actions and uses the public target syntax such as `dev` or `dev:planner` where supported.

Action semantics:

- `open` opens through a local opener. Without `opener`, it uses `auto-terminal`. Without `intent`, workspace opens infer `workspace_dashboard` and target opens infer `attach_target`.
- `workspace_dashboard` runs `cc-branch dashboard` in a command-capable terminal opener.
- `attach_target` ensures the slot exists and opens the target through the selected opener. Terminal openers run `cc-branch attach <target>` or the terminal-runtime command. VS Code and Cursor use a generated `.code-workspace` containing a single target task.
- `project_folder` opens the project directory without attaching tmux. Terminal openers open an interactive shell in that directory; editor openers such as VS Code and Cursor open the folder.
- `launch` starts tmux sessions in the background and does not open a visible terminal window.
- `restart` recreates the workspace or target in the background.
- `stop` stops the workspace or target.
- `sync` restarts changed, missing, or untracked tmux windows so the running workspace matches the saved config.

GUI semantics:

- The GUI has one tool selector and two primary buttons: "Open workspace" and "Open project directory".
- "Open workspace" adapts to the selected tool. Terminal openers run dashboard or attach commands. Warp uses Launch Configurations and can open one arranged layout. VS Code and Cursor open a generated `.code-workspace` file. For tmux slots, the workspace file contains one attach task per slot, not one task per tmux window; terminal-runtime slots are represented by their visible shell commands.
- "Open project directory" uses the same selected tool. Terminal tools open a shell in the project directory; editor tools open the folder. The button is enabled only when that tool supports `open_project`.
- Slot-level "Open terminal" buttons use the same selected tool as the workspace and project actions. Terminal openers run commands directly; VS Code and Cursor open a generated `.code-workspace` task for that target.

Runtime behavior:

- `runtime: tmux` is reusable. Opening the same workspace from Terminal, Warp, iTerm2, or another supported terminal attaches to the existing tmux sessions.
- `runtime: terminal` is external and not reusable. Opening it starts a new visible process; stopping it means closing that terminal window manually.
- If a workspace has only `runtime: terminal` slots, `open` uses the selected terminal opener to run those commands directly instead of opening a tmux dashboard.
- Warp supports command execution through Launch Configurations. For pure terminal-runtime workspaces, CC Branch writes one temporary launch configuration so Warp can open a single arranged layout instead of many unrelated windows.
- VS Code and Cursor workspace opens rely on editor tasks with `runOn: folderOpen`; the editor may ask the user to trust or allow automatic tasks before running them.

### `GET /api/openers`

Returns local opener metadata:

```json
{
  "default": "auto-terminal",
  "openers": [
    {
      "id": "auto-terminal",
      "label": "System Terminal",
      "kind": "terminal",
      "available": true,
      "capabilities": ["run_command", "dashboard", "attach_target", "open_project"],
      "source": "builtin"
    },
    {
      "id": "vscode",
      "label": "VS Code",
      "kind": "editor",
      "available": true,
      "capabilities": ["open_project", "workspace_file"],
      "source": "builtin",
      "executable": "/usr/local/bin/code"
    },
    {
      "id": "warp",
      "label": "Warp",
      "kind": "terminal",
      "available": true,
      "capabilities": ["run_command", "dashboard", "attach_target", "open_project", "layout"],
      "source": "builtin",
      "executable": "/Applications/Warp.app"
    }
  ]
}
```

### `GET /api/agents`

Returns effective agent profiles for the selected project. These profiles are available to the Config Editor agent dropdown without expanding built-in defaults into `.cc-branch/config.yaml`.

```json
{
  "agents": [
    {
      "id": "codex",
      "command": "codex",
      "resume_mode": "flag",
      "resume_template": "resume {session_id}",
      "create_mode": "none",
      "create_template": "",
      "label_template": "{project}/{slot}/{window}",
      "label_mode": "metadata",
      "rename_template": ""
    }
  ]
}
```

Unavailable openers are still returned with `available: false` and a `reason` so the UI can explain why they cannot be selected.

## 6. Security model

### Current behavior

- static file paths are canonicalized to prevent traversal
- CORS reflects the request origin instead of using `*`
- the CLI and backend support bearer-token/cookie enforcement for the Web UI and all APIs
- non-loopback binds require `--token` or `CC_BRANCH_WEB_TOKEN`
- API callers may reference only registered opener IDs; they cannot submit arbitrary commands through `/api/action`
- editor openers such as VS Code and Cursor cannot receive arbitrary browser-provided shell commands; workspace opens use generated `.code-workspace` tasks derived from the resolved workspace plan, and project opens pass only the project directory
- terminal openers run only commands produced from the resolved workspace plan; the browser cannot provide arbitrary shell text

## 7. Data model alignment

The Web UI uses the same typed core as the CLI:

- config editing, save conflict checks, initialization, and project probing go
  through `application.config_workflows`
- status payloads go through `application.workspace_status`
- doctor payloads go through `application.diagnostics`
- action POSTs go through `application.workspace_actions.execute_workspace_action`

That means the browser view and terminal view are backed by the same canonical pipeline.

## 8. Shipped vs not-yet-shipped

### Shipped now

- bundled static frontend
- status/config/doctor APIs
- profile discovery
- init from the UI/backend
- config save
- launch/restart/stop actions
- project-path-scoped reads/writes
- server-side project probing
- `serve` startup from config-less directories

### Not guaranteed by current CLI surface

- live push/WebSocket status updates
- arbitrary filesystem browsing or directory creation from the Web UI

If you need to describe current behavior, prefer this document over older design explorations.

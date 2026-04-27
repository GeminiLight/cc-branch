# CC Branch Web UI User Flows

> Status: updated for the current shipped Web UI backend and bundled frontend.

## 1. Main flows

### 1.1 Open the current project in the browser

```text
User runs `cc-branch serve`
  -> Python server starts on 127.0.0.1:8080 by default
  -> Browser loads bundled static app
  -> Frontend requests /api/status, /api/config, /api/doctor
  -> User sees workspace state, or setup state if no config exists
```

If the user binds the server to a non-loopback host, they must provide `--token` or `CC_BRANCH_WEB_TOKEN` before the backend starts. With a token configured, the first browser visit uses the printed `/?token=...` URL; after that, the browser uses an HttpOnly same-origin cookie for the Web UI and all `/api/*` calls.

### 1.2 Initialize a new workspace from the UI/backend

```text
Project has no config yet
  -> User runs `cc-branch serve` directly in that directory
  -> Frontend receives needs_init from /api/status or /api/project/probe
  -> Frontend/backend requests available profiles via /api/profiles
  -> User chooses profile
  -> Frontend posts to /api/init
  -> Backend runs bootstrap flow and writes config/state
  -> Frontend refreshes status/config/doctor panels
```

### 1.3 Inspect and edit config

```text
User opens Config view
  -> Frontend loads /api/config
  -> User edits YAML
  -> Frontend posts updated content to /api/config
  -> Backend writes file
  -> User refreshes status / doctor as needed
```

### 1.4 Inspect workspace health

```text
User opens Doctor view
  -> Frontend requests /api/doctor
  -> Backend returns current report
  -> User sees missing commands, unknown agents, invalid env keys, etc.
```

### 1.5 Open a workspace or slot in a terminal

```text
User clicks "Open workspace in terminal"
  -> Frontend posts to /api/action with {action: "open", opener: "auto-terminal", intent: "workspace_dashboard"}
  -> Backend asks the selected local opener to open a terminal
  -> New terminal runs `cc-branch dashboard`
```

For a slot-level button:

```text
User clicks "Open terminal" on a slot
  -> Frontend posts to /api/action with {action: "open", target: "dev", opener: "auto-terminal", intent: "attach_target"}
  -> Backend ensures the tmux slot exists
  -> New terminal runs `cc-branch attach dev`
```

The terminal is opened by the local Python backend, not by the browser itself. If the backend cannot find a supported terminal emulator or the OS blocks automation, the UI shows the returned error.

### 1.6 Open a project in an editor

```text
User chooses "VS Code" or "Cursor" from Open With
  -> Frontend posts to /api/action with {action: "open", opener: "vscode", intent: "project_folder"}
  -> Backend runs the registered editor CLI, such as `code <project-root>`
  -> Editor opens the project folder
  -> No tmux attach is implied
```

Editor openers are not treated as terminals. If the user tries to attach a slot through an opener that only supports `project_folder`, the backend rejects the request instead of silently doing a different action.

### 1.7 Start without opening a terminal

```text
User clicks "Start in background"
  -> Frontend posts to /api/action with {action: "launch"}
  -> Backend creates tmux sessions/windows with detach=true
  -> No visible terminal window is opened
  -> Frontend refreshes /api/status
```

### 1.8 Stop a running slot

```text
User triggers a stop action
  -> Frontend posts to /api/action with {action: "stop", target: ...}
  -> Backend calls tmux kill-session
  -> Frontend refreshes /api/status
```

Restart uses the same `/api/action` endpoint with `action: "restart"`.

## 2. Multi-project flow

The backend can scope requests to another project path using `project_path`.

```text
Frontend chooses another project directory
  -> Calls /api/status?project_path=/abs/path
  -> Calls /api/config?project_path=/abs/path
  -> Calls /api/doctor?project_path=/abs/path
  -> Same backend serves multiple projects without being tied to a single cwd view
```

## 3. Desktop-wrapper flow

A desktop wrapper can launch the backend with explicit paths:

```text
Wrapper sets CC_BRANCH_CONFIG=/abs/path/.cc-branch.yaml
Wrapper sets CC_BRANCH_STATE=/abs/path/.cc-branch.state.toml
Wrapper starts Python backend
  -> WorkspaceContext uses overridden paths
  -> Web UI works without depending on process cwd
```

## 4. Current UX assumptions

- the frontend is bundled and served by Python
- `cc-branch serve` can start before a workspace config exists
- status/config/doctor are the primary views
- init and config save are real backend capabilities
- open, launch, restart, and stop are exposed through `/api/action`

## 5. Current limitations

- no WebSocket/live-push status stream
- no arbitrary filesystem browser or directory creation flow in the shipped CLI surface
- no guarantee that every older mockup or design tab is fully implemented in the current frontend

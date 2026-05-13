# CC Branch Web UI User Flows

> **Status**: ⚠️ Verify accuracy. Describes expected user flows for the shipped Web UI,
> but the frontend implementation should be verified against [`docs/webui-spec.md`](webui-spec.md)
> before treating all described flows as guaranteed shipped behavior.
>
> The authoritative reference for the shipped Web UI surface is
> [`docs/webui-spec.md`](webui-spec.md).

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

### 1.5 Open a workspace or tab

```text
User selects a tool, then clicks "Open workspace"
  -> Frontend posts to /api/action with {action: "open", opener: selectedTool, intent: "workspace_dashboard"}
  -> Backend adapts the workspace open to the selected tool
```

Terminal tools run dashboard or attach commands. Warp writes a stable Launch Configuration under Warp's launch configuration directory and opens it with Warp's `warp://launch/...` app link. VS Code and Cursor open the real project folder; on macOS they also create integrated terminals for the workspace commands.

The dashboard itself is still tmux-backed, so opening the same workspace from a different terminal attaches to the same reusable sessions.

For a tab-level button:

```text
User clicks "Open" on a tab
  -> Frontend posts to /api/action with {action: "open", target: "dev", opener: selectedTool, intent: "attach_target"}
  -> Backend ensures the tmux-backed tab exists
  -> The selected tool opens the target
```

Terminal tools run `cc-branch attach <target>` or the direct-layout command. On macOS, VS Code and Cursor open the real project folder and create an integrated terminal for that target. The tool is opened by the local Python backend, not by the browser itself. If the backend cannot find a supported opener or the OS blocks automation, the UI shows the returned error.

### 1.6 Open a project directory

```text
User clicks "Open project directory"
  -> Frontend posts to /api/action with {action: "open", opener: system-file-manager, intent: "project_folder"}
  -> Backend opens the folder in the system file manager
  -> No tmux attach is implied
```

Project directory open is intentionally separate from workspace open. It uses the system file manager so the user always lands in a normal folder view instead of a terminal or editor-specific project mode.

Workspace open still adapts to the selected tool. Terminal tools run dashboard or attach commands. Warp writes a stable Launch Configuration under Warp's launch configuration directory and opens it with Warp's `warp://launch/...` app link. VS Code and Cursor open the real project folder; on macOS they also create integrated terminals for the workspace commands.

### 1.6.1 Direct-layout workspace

```text
User opens a workspace that has only direct-layout tabs
  -> Frontend still posts {action: "open", intent: "workspace_dashboard"}
  -> Backend sees there are no tmux-backed tabs
  -> Backend runs the direct-layout pane commands through the selected opener
```

Direct-layout panes are not reusable. Every open starts a new external terminal process. Warp is the exception only in presentation: CC Branch can group multiple direct pane commands into one Warp Launch Configuration layout, but those processes still are not tmux sessions and cannot be stopped or reattached by CC Branch.

### 1.7 Start without opening a terminal

```text
User clicks "Start in background"
  -> Frontend posts to /api/action with {action: "launch"}
  -> Backend creates tmux sessions/panes with detach=true
  -> No visible terminal pane is opened
  -> Frontend refreshes /api/status
```

### 1.8 Stop a running tab

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
Wrapper sets CC_BRANCH_CONFIG=/abs/path/.cc-branch/config.yaml
Wrapper sets CC_BRANCH_STATE=/abs/path/.cc-branch/state.yaml
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

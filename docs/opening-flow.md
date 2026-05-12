# 打开工作空间的当前实现

这份文档说明 Web UI 里点“打开工作空间”“打开项目目录”“打开某个 slot/window”时，当前代码会走什么路径，以及用户最终会看到什么窗口形态。

## 入口

Web UI 的 Dashboard 不直接调用 Cursor、VS Code、Warp 或终端。它只把用户意图发给后端：

```text
Dashboard
  -> POST /api/action
     {
       action: "open",
       opener: "warp" | "vscode" | "cursor" | "auto-terminal" | ...,
       target?: "slot" | "slot:window",
       intent:
         "workspace_dashboard" | "attach_target" | "project_folder"
     }
```

后端入口是 `WorkspaceActionExecutor.execute()`。当 `action == "open"` 时，它会进入 `WorkspaceOpenActions.open_workspace()`，再根据 intent 和 opener 能力分流。

## 三种用户意图

```text
打开工作空间
  intent = workspace_dashboard
  target = undefined

打开某个 slot 或 window
  intent = attach_target
  target = "dev" 或 "dev:planner"

打开项目目录
  intent = project_folder
  target = undefined
```

当前 UI 上的“打开项目目录”固定走系统文件管理器：

```text
macOS    -> Finder
Windows  -> File Explorer
Linux    -> xdg-open / File Manager
```

它不是“在 Cursor/VS Code/Warp 里打开项目”，而是“在系统文件夹里打开这个目录”。

## opener 能力模型

每个 opener 会声明自己支持什么能力：

```text
System Terminal / Terminal.app / iTerm2 / Windows Terminal / Linux terminals
  run_command
  dashboard
  attach_target
  open_project

Warp
  run_command
  dashboard
  attach_target
  open_project
  layout

VS Code / Cursor
  open_project
  workspace_file

Finder / File Explorer / File Manager
  open_project
```

关键区别：

```text
layout
  可以一次打开多个命令，并尽量排成一个可视布局。
  当前主要是 Warp 使用。

workspace_file
  可以打开编辑器工作空间，并把多个命令做成编辑器任务或集成终端。
  当前是 VS Code / Cursor 使用。

run_command
  可以开一个终端并运行一条命令。
  普通终端通常没有统一的多 pane 布局能力，所以多条命令会变成多个终端窗口。
```

## 打开工作空间

假设配置长这样：

```text
workspace
  tmux slot: dev
    window: planner
    window: builder

  terminal slot: ui
    window: codex-ui

  terminal slot: spec
    window: codex-spec
```

### 选择 Warp 后点“打开工作空间”

Warp 支持 `layout`，所以后端会：

1. 先确保 tmux slot 已经启动。
2. 为 tmux slot 生成 attach 命令：`cc-branch attach dev`。
3. 为 terminal slot 生成真实启动命令，例如 `codex ...`、`claude ...`。
4. 写入稳定的 Warp launch config，例如 `cc-branch-cli-workspace.yaml`，配置里的 `name` 类似 `CC Branch cli-workspace`。
5. 打开 `warp://launch/<launch-config-name>`。

用户大概会看到：

```text
Warp window: CC Branch: cli-workspace
┌───────────────────────────────────────────┐
│ Tab: CC Branch: cli-workspace             │
├──────────────────────┬────────────────────┤
│ Pane 1               │ Pane 2             │
│ cwd: project         │ cwd: project       │
│ cc-branch attach dev │ codex ...          │
├──────────────────────┼────────────────────┤
│ Pane 3               │ Pane 4             │
│ cwd: project         │ cwd: project       │
│ codex ...            │ claude ...         │
└──────────────────────┴────────────────────┘
```

注意：tmux slot 在 Warp 里表现为一个 pane，pane 内部 attach 到 tmux session。tmux 自己的多 window 切换发生在这个 pane 里的 tmux UI 中。

```text
Warp pane
┌───────────────────────────────────────────┐
│ tmux session: dev                         │
│ windows: planner | builder | reviewer     │
│                                           │
│ 当前显示其中一个 tmux window              │
└───────────────────────────────────────────┘
```

### 选择 VS Code / Cursor 后点“打开工作空间”

VS Code / Cursor 支持 `workspace_file`。

当前实现为了避免编辑器标题出现 `cli-workspace-vscode-<hash>.code-workspace` 这种临时工作空间名，会优先正常打开项目目录：

```text
code -n /path/to/project
cursor -n /path/to/project
```

在 macOS 上，随后会通过 AppleScript 在编辑器里创建集成终端，把命令粘贴进去并回车。

用户大概会看到：

```text
VS Code / Cursor
┌───────────────────────────────────────────┐
│ Explorer                                  │
│   cli-workspace                           │
│     .cc-branch                            │
│     apps                                  │
│     cc_branch                             │
│                                           │
├───────────────────────────────────────────┤
│ Integrated Terminal                       │
│ ┌───────────────────────────────────────┐ │
│ │ terminal 1: cc-branch attach dev      │ │
│ ├───────────────────────────────────────┤ │
│ │ terminal 2: codex ...                 │ │
│ ├───────────────────────────────────────┤ │
│ │ terminal 3: claude ...                │ │
│ └───────────────────────────────────────┘ │
└───────────────────────────────────────────┘
```

这依赖 macOS Accessibility 权限。没有权限时，项目目录可能已经打开，但集成终端创建会失败，并提示授予权限。

在非 macOS 上，当前实现不再生成临时 `.code-workspace` 文件，也会打开真实项目目录：

```text
VS Code / Cursor
┌───────────────────────────────────────────┐
│ Explorer                                  │
│   cli-workspace                           │
│     .cc-branch                            │
│     apps                                  │
│     cc_branch                             │
└───────────────────────────────────────────┘
```

目前只有 macOS 分支会自动创建集成终端；非 macOS 分支先保证不再污染编辑器标题和 Explorer 结构。

### 选择普通 Terminal 后点“打开工作空间”

普通 terminal 没有通用 layout 能力。当前策略是：

1. 先确保 tmux slot 启动。
2. 打开 dashboard 或 attach 命令。
3. 如果还有 terminal slot，再为每个 terminal slot/window 单独打开一个终端窗口。

用户大概会看到：

```text
Terminal window 1
┌──────────────────────────────┐
│ cd project                   │
│ cc-branch dashboard / attach │
└──────────────────────────────┘

Terminal window 2
┌──────────────────────────────┐
│ cd project                   │
│ codex ...                    │
└──────────────────────────────┘

Terminal window 3
┌──────────────────────────────┐
│ cd project                   │
│ claude ...                   │
└──────────────────────────────┘
```

也就是说普通终端的结果更像“多个独立窗口”，不是一个统一 pane 布局。

## 打开单个 slot

### 打开 tmux slot

例如点 `dev` 的“打开”：

```text
intent = attach_target
target = "dev"
```

后端会先确保 `dev` 这个 tmux slot 已经启动，然后根据 opener 分流。

Warp：

```text
Warp window
┌──────────────────────────────┐
│ cc-branch attach dev         │
│                              │
│ 进入 tmux session: dev       │
└──────────────────────────────┘
```

VS Code / Cursor：

```text
Editor
┌──────────────────────────────┐
│ Project folder               │
├──────────────────────────────┤
│ Integrated terminal          │
│ cc-branch attach dev         │
└──────────────────────────────┘
```

普通 Terminal：

```text
Terminal window
┌──────────────────────────────┐
│ cd project                   │
│ cc-branch attach dev         │
└──────────────────────────────┘
```

### 打开 terminal slot

例如点 `ui` 的“打开”：

```text
intent = attach_target
target = "ui"
```

terminal runtime 不会 attach tmux。它会直接运行这个 slot/window 的 launch command。

```text
Terminal / Warp / Editor integrated terminal
┌──────────────────────────────┐
│ cd <window.cwd>              │
│ <window.launch_command>      │
└──────────────────────────────┘
```

如果这个 terminal slot 里有多个 window，点 slot 级“打开”会为它的每个 window 生成一条命令。

## 打开单个 window

例如点 `dev:planner` 的“打开”：

```text
intent = attach_target
target = "dev:planner"
```

如果这是 tmux window：

```text
cc-branch attach dev:planner
```

最终看到的是：

```text
Terminal / Warp pane / Editor integrated terminal
┌──────────────────────────────┐
│ cd <window.cwd>              │
│ cc-branch attach dev:planner │
│                              │
│ 进入 tmux session dev        │
│ 并切到 planner window        │
└──────────────────────────────┘
```

如果这是 terminal window：

```text
<window.launch_command>
```

最终看到的是：

```text
Terminal / Warp pane / Editor integrated terminal
┌──────────────────────────────┐
│ cd <window.cwd>              │
│ codex ... / claude ... / ... │
└──────────────────────────────┘
```

## 当前实现的一个关键原则

tmux 和 terminal runtime 的语义不一样：

```text
tmux runtime
  cc-branch 负责先启动/维护 tmux session。
  打开时通常是 attach 到已有 session/window。

terminal runtime
  不常驻在 cc-branch 管理的 tmux session 里。
  打开时就是在用户选择的工具里直接运行 launch command。
```

所以同样叫“打开”，底层命令可能不同：

```text
tmux slot/window:
  cc-branch attach <target>

terminal slot/window:
  <window.launch_command>
```

## 当前可能需要继续校准的点

1. VS Code / Cursor 现在统一正常打开项目目录；macOS 会继续自动创建集成终端，非 macOS 不再生成 `.code-workspace` 临时文件。
2. Warp 的“打开工作空间”是一个稳定的 Warp launch config，多个命令在同一个 Warp tab/panes 里；tmux slot 本身只占一个 pane，tmux 内部再管理多个 window。
3. 普通 terminal 没有统一多 pane 能力，所以多命令会开多个终端窗口。
4. “打开项目目录”现在固定是系统文件管理器，不受上方选择的 Cursor/VS Code/Warp 影响。
5. 自定义 opener 如果只声明 `open_project`，会被当作“只打开项目目录”；如果声明 `run_command`，会按命令运行器处理。

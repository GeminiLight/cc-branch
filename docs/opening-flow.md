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
  可以用编辑器机制承载多个命令。
  当前是 VS Code / Cursor 使用；实现上打开真实项目目录，并通过 folder-open tasks 创建集成终端。

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

当前实现不会生成 `.code-workspace` 临时文件。后端会先为本次工作空间生成 VS Code/Cursor tasks：

```text
.cc-branch/.generated/vscode-tasks.json
  CC Branch 生成的任务源文件

.vscode/tasks.json
  编辑器实际读取的桥接文件
```

如果项目没有 `.vscode/tasks.json`，CC Branch 会创建桥接文件。
如果用户已有自己的 `.vscode/tasks.json`，CC Branch 会合并自己的任务并保留用户任务。
如果这个文件无法解析或无法更新，打开动作会直接失败并显示错误，避免“编辑器打开了但终端没有创建”的假成功。

然后它正常打开真实项目目录：

```text
code -n /path/to/project
cursor -n /path/to/project
```

编辑器在 folder open 时运行这些 tasks。tasks 使用 `runOptions.runOn = "folderOpen"` 自动启动，并用 `presentation.group` 表达同一个标签页下的 split terminal 分组。

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

这个路径不依赖 macOS Accessibility，也不通过 AppleScript 粘贴命令。只要 VS Code/Cursor 支持 folder-open tasks，macOS、Windows、Linux 都走同一个机制。

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

这同样通过 `.vscode/tasks.json` 的 folder-open task bridge 创建终端；如果 bridge 无法安装，后端会返回明确错误。

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

1. VS Code / Cursor 现在统一正常打开项目目录，并通过 `.vscode/tasks.json` 的 folder-open task bridge 创建集成终端；不再生成 `.code-workspace` 临时文件，也不再依赖 AppleScript。
2. Warp 的“打开工作空间”是一个稳定的 Warp launch config，多个命令在同一个 Warp tab/panes 里；tmux slot 本身只占一个 pane，tmux 内部再管理多个 window。
3. 普通 terminal 没有统一多 pane 能力，所以多命令会开多个终端窗口。
4. “打开项目目录”现在固定是系统文件管理器，不受上方选择的 Cursor/VS Code/Warp 影响。
5. 自定义 opener 如果只声明 `open_project`，会被当作“只打开项目目录”；如果声明 `run_command`，会按命令运行器处理。

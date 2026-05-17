# Workspace 术语规范

状态：当前规范。产品、配置文件、Web UI 和文档应优先使用这里的术语。

## 核心决策

CC Branch 的用户侧模型是：

```text
Workspace
└─ Tab
   └─ Pane
      └─ Agent / Command
```

不要再把 `slot` / `window` 作为用户可见主术语。它们只允许作为内部兼容实现名、状态文件字段或 tmux 特定诊断细节出现。

## 标准术语

| 术语 | 中文 | 含义 | 示例 |
|---|---|---|---|
| Workspace | 工作空间 | 一个项目的一套可重复打开的终端工作台。 | `cli-workspace` |
| Tab | 标签页 | 一组工作上下文，可切换，可包含多个 Pane。 | `dev`, `review`, `servers` |
| Pane | 窗格 | 最小执行单元，运行一个 Agent 或命令。 | `planner`, `server` |
| Agent | Agent | 可复用的 AI CLI 工具配置。 | `codex`, `claude` |
| Command | 命令 | Pane 内执行的 shell 命令。 | `pnpm dev` |
| openWith | 打开方式 | 默认用哪个本机应用打开工作空间。 | `cursor`, `vscode`, `warp` |
| layoutBackend | 布局后端 | 谁负责 Tab/Pane 的启动和生命周期。 | `tmux`, `direct` |
| shell | Shell | Pane 命令的解释器；项目级只作为默认值。 | `system-default`, `zsh`, `pwsh` |
| State | 状态 | 本机运行元数据，不提交到仓库。 | session id, label |

## 配置字段

公开 YAML 使用这组字段：

```yaml
version: 2
project: cli-workspace
root: .

openWith: cursor
layoutBackend: tmux

defaults:
  shell: system-default

tabs:
  - name: dev
    panes:
      - name: planner
        agent: codex
        session: auto
      - name: server
        command: pnpm dev
        shell: zsh
```

### `openWith`

用户在哪里打开/查看工作空间。它是产品语言，不等同于内部 opener 适配器。

常见值：

- `cursor`
- `vscode`
- `warp`
- `iterm`
- `terminal`
- `auto-terminal`

内部实现可以继续使用 opener registry，但文档和 GUI 应写“打开方式”或 `openWith`。

### `layoutBackend`

谁负责布局和生命周期：

- `tmux`：CC Branch 可以稳定管理可恢复的 Tab/Pane、后台启动、attach、stop、dashboard。
- `direct`：不使用布局后端，直接通过打开方式启动命令；通常不保证持久化和后台生命周期。

不要使用 `runtime: terminal` 作为公开主概念。旧配置可以读，但新文档、新模板和 GUI 应使用 `layoutBackend`。

### `defaults.shell`

项目级默认 Shell，不是强制全局 Shell。

解析优先级：

```text
pane.shell
→ defaults.shell
→ system default shell
```

`shell` 属于 Pane execution context。Tab 不配置 shell。

支持的简单值：

- `system-default`
- `zsh`
- `bash`
- `pwsh`
- `cmd`

高级自定义值：

```yaml
shell:
  command: fish
  args: ["-l"]
```

GUI 首屏只展示常见值。自定义 Shell 可以先通过 YAML 管理。

## 内部兼容边界

当前代码仍有内部模型名：

| 内部名 | 用户侧名 | 说明 |
|---|---|---|
| `SlotConfig` | Tab | 历史内部模型，planner/state 仍使用。 |
| `WindowConfig` | Pane | 历史内部模型，代表可执行 Pane。 |
| `runtime` | layout backend mapping | 内部运行策略字段；公开 schema 用 `layoutBackend`。 |
| `opener` / `default_opener` | openWith | opener 是实现适配器，openWith 是用户配置。 |

这些内部名不应该出现在新的用户文档、GUI 标题、按钮、空状态和入门模板里。

## 外部工具映射

| CC Branch | tmux | VS Code / Cursor | Warp / iTerm / Terminal |
|---|---|---|---|
| Workspace | session group | project folder + terminal surface | terminal workspace/window |
| Tab | session/window grouping | terminal/editor tab concept | tab/window |
| Pane | pane/window command target | split terminal pane | pane/tab/window fallback |
| openWith | attach/open adapter | editor opener | terminal opener |
| layoutBackend | tmux | direct or future host-native | direct or future host-native |

注意：VS Code、Cursor、Warp 视觉上有 tabs/panes，不代表 CC Branch 现在能可靠控制它们的原生布局。因此布局能力要由 `layoutBackend` 表达，而不是由 `openWith` 暗示。

## 文案规则

使用：

- Add tab / 添加标签页
- Add pane / 添加窗格
- Move pane / 移动窗格
- Default open with / 默认打开方式
- Layout backend / 布局后端
- Default shell / 默认 Shell
- Bind session / 绑定会话

避免：

- Add slot
- Add window
- terminal runtime
- Project opener
- native layout

## 迁移策略

1. 新配置、新模板、新文档只写 `tabs/panes/openWith/layoutBackend/defaults.shell`。
2. 旧 `slots/windows/runtime/default_opener` 可以继续读入，作为未发布前的迁移兼容。
3. Web UI 表单使用 Tab/Pane 文案，内部变量名可以分阶段迁移。
4. State 文件可暂时保留 `slots/windows`，因为它是本机运行元数据，不是公开配置界面。
5. 后续重构再把内部 `SlotConfig` / `WindowConfig` 改名为 `TabConfig` / `PaneConfig`，同时提供状态迁移。

# CC Branch 使用指南

这份文档面向已经准备开始使用 CC Branch 的用户。它重点解释怎么初始化、怎么配置、怎么日常操作，以及出了问题时先看哪里。

## 安装与环境

### 环境要求

- 你会在配置里实际使用到的命令行工具
- 只有通过 PyPI 或源码安装时才需要 Python 3.10 或更高版本
- 只有使用 `layoutBackend: tmux` 时才需要 `tmux`

没有 `tmux` 时，可以使用默认的 `layoutBackend: direct`。这些窗格会作为外部终端或编辑器进程打开，不具备 tmux 的复用、后台生命周期或 tmux 级 attach。

### 安装

Homebrew tap 发布后，macOS / Linux 推荐：

```bash
brew install GeminiLight/cc-branch/cc-branch
```

Python 用户推荐：

```bash
pipx install cc-branch
```

只在虚拟环境里使用 `pip install cc-branch`。

### 验证

```bash
cc-branch --help
ccb --help
```

## 初始化项目

### 推荐方式

```bash
cc-branch init
```

这一步通常会完成下面几件事：

- 检查可选的 `tmux`
- 探测常见命令行工具
- 按模板生成起步配置
- 创建 `.cc-branch/state.yaml`
- 在需要时补齐 `session_id`
- 更新 `.gitignore`

`development` 是默认模板；检测到可用 Agent CLI 时，session metadata 会自动初始化。产品/设计工作可以用 `--profile design`，只需要一个窗格时可以用 `--profile minimal`。

### 最简方式

```bash
cc-branch init --minimal
```

如果你已经知道自己要写什么配置，只想先拿到基础文件，可以用这个模式。

### 可选模板

```bash
cc-branch init --profile design
cc-branch init --profile minimal
```

## 配置文件和状态文件

### 配置文件

CC Branch 只自动读取 `.cc-branch/config.yaml`。首次发版不保留旧格式兼容。

### 两个关键文件

- `.cc-branch/config.yaml`：项目配置，适合提交到仓库
- `.cc-branch/state.yaml`：本地运行状态，通常不建议提交

状态文件里常见的信息包括：

- `session_id`
- `label`
- `agent`
- `tab`
- `pane`

## 配置怎么写

### 顶层结构

```yaml
version: 2
project: "my-project"
root: "."

display:
  mode: "grid"
  columns: 2
  dashboard: true

tabs: []
```

### `display`

- `mode`：总览面板的布局方式
- `columns`：`grid` 模式下的列数
- `dashboard`：旧配置字段；当前需要显式运行 `dashboard` 或 `start --dashboard` 进入总览面板

### `agents`

`agents` 是可选的 agent profile 覆盖区，不是每个项目都必须维护的基础配置。

内置 agent profile 默认可用：claude、codex、gemini、cursor、kimi。也就是说，普通项目可以直接在 pane 里写：

```yaml
tabs:
  - name: "coding"
    panes:
      - name: "planner"
        agent: "codex"
```

只有在需要覆盖默认启动方式，或添加自定义 agent 时，才需要写 `agents`。

有效 agent profile 的合并顺序是：

1. 内置 `cc_branch/agents.yaml`
2. 用户全局 `~/.cc-branch/agents.yaml`
3. 工作区 `.cc-branch/agents.yaml`
4. 当前 `.cc-branch/config.yaml` 里的 `agents`

后面的层级覆盖前面的层级，并且是字段级覆盖。例如只改 `command` 时，默认的 `resume_template`、`label_template` 仍然保留：

```yaml
agents:
  codex:
    command: "codex --sandbox read-only"
```

每个 agent 可以声明这些字段：

- `command`
- `resume_mode`
- `resume_template`
- `create_mode`
- `create_template`
- `label_template`
- `label_mode`
- `rename_template`

如需添加自定义 agent，创建 `~/.cc-branch/agents.yaml`：

```yaml
agents:
  my-agent:
    command: my-agent
    resume_mode: flag
    resume_template: "--restore {session_id}"
```

可用模板变量：`{session_id}`、`{project}`、`{tab}`、`{pane}`、`{label}`。`{slot}` 和 `{window}` 仍是内部兼容别名，新配置不要继续使用。

`resume_mode` 说明：

- `flag` — 启动时附加 flag（如 `codex resume <id>`）
- `internal` — 启动后发送 post-launch 命令恢复
- `none` — 不处理恢复，直接运行命令

### `tabs`

每个 `tab` 是工作区里的一个顶层上下文。`layoutBackend` 决定它由普通本地进程承载，还是由 tmux 承载。

常见字段有：

- `name`
- `layoutBackend`
- `opener`
- `cwd`
- `env`
- `panes`
- `command`
- `title`
- `agent`
- `session`
- `label`

### `panes`

窗格层常见字段有：

- `name`
- `agent`
- `command`
- `cwd`
- `env`
- `session`
- `label`
- `label_template`
- `resume_mode`
- `resume_template`
- `create_mode`
- `create_template`
- `label_mode`
- `rename_template`

## 计划和运行时规则

### `direct` 布局会被归一化

```yaml
tabs:
  - name: "scratch"
    layoutBackend: "direct"
    panes:
      - name: "scratch"
        command: "zsh"
```

这类写法会通过本机终端或编辑器 opener 打开。它不会创建 tmux 会话，也不会被 stop 当作可持久化的 tmux 目标。

### 路径如何解析

- tab 的 `cwd` 相对于 `root`
- pane 的 `cwd` 相对于 tab 的 `cwd`
- 绝对路径会保持不变

### 环境变量如何合并

- tab 的 `env` 和 pane 的 `env` 会合并
- pane 同名字段会覆盖 tab
- 最终会注入到实际启动命令前

### 创建和恢复如何处理

CC Branch 会根据配置和本地状态，生成最终 `launch_command` 与 `post_launch_commands`。

Agent 会话只需要一个字段：

```yaml
session: auto   # 默认，可省略；已有绑定就恢复，没有就启动新会话并尽量记住
session: fresh  # 每次启动都开新会话，不复用 state
session: "..."  # 显式恢复这个真实 session id
```

真实的运行时会话 ID 保存在 `.cc-branch/state.yaml`，不需要写进项目配置。对于 Codex、Claude、Gemini、Cursor、Kimi 等可扫描本地会话的 Agent，`session: auto` 启动后会尝试把新创建的 session 绑定回 state；如果暂时识别不到，状态会显示为等待识别，后续仍可手动选择历史会话。

常见模式包括：

- `resume_mode = flag`
- `resume_mode = internal`
- `create_mode = generated_uuid`

## 常用命令

### `plan`

```bash
cc-branch plan [--write-state] [--json]
```

适合在正式启动前先确认：

- 命令是否正确
- 目录是否正确
- agent session 是自动、每次新建，还是显式恢复
- label 和附加命令是否符合预期

### `start`

```bash
cc-branch start [--prepare] [--detach] [--dashboard]
```

它会按配置创建可复用 tmux 会话或直接启动本地命令，并默认进入第一个可 attach 的标签页。`--detach` 只创建 tmux session，不会 attach，也不会打开 direct 布局的外部进程。

需要总览面板时，使用 `cc-branch dashboard` 或 `cc-branch start --dashboard`。`start` 不会因为 `display.dashboard` 配置而静默切换到面板。

### `open`

```bash
cc-branch open [tab[:pane]] [--opener auto-terminal|warp|vscode|cursor]
cc-branch open --project-dir [--opener auto-terminal|warp|vscode|cursor]
```

它是“打开可见工作空间”的统一入口。`open` 会按 opener 适配 Terminal、Warp、VS Code、Cursor；打开 tmux 标签页时会先确保 tmux session 存在，打开 direct 布局窗格时会启动外部终端或编辑器进程。`--project-dir` 不会 attach workspace：终端类工具会在项目目录打开一个交互 shell，编辑器类工具会打开项目文件夹。

### `status`

```bash
cc-branch status [--write-state] [--json]
```

常见输出包括：

- tab 是否在运行
- pane 是否存在
- 当前 `session_id`
- 当前 label
- agent 名称

### `attach`

```bash
cc-branch attach <tab>
cc-branch attach <tab>:<pane>
```

### `stop`

```bash
cc-branch stop
cc-branch stop dev
cc-branch stop dev:planner
```

### `restart`

```bash
cc-branch restart
cc-branch restart dev
cc-branch restart dev:planner --detach
```

### `dashboard`

```bash
cc-branch dashboard [--prepare]
```

### `doctor`

```bash
cc-branch doctor [--write-state] [--fix]
```

常见检查包括：

- `tmux` 是否存在
- 配置里的命令是否存在
- 是否有重复的 tmux 会话或窗口
- agent 名称是否无效
- 环境变量名是否非法
- `cwd` 是否缺失
- 启动命令是否缺失
- 需要恢复时是否缺少 `session_id`

`doctor --fix` 当前会尝试处理：

- 创建缺失目录
- 为支持 `generated_uuid` 的窗口补写缺失的 `session_id`
- 补充 `.gitignore`

### `sync`

```bash
cc-branch sync [tab[:pane]] [--dry-run] [--yes] [--stop-removed]
```

修改 `.cc-branch/config.yaml` 后，已经运行的 tmux pane 不会自动换命令。`sync --dry-run` 会列出需要重启的 tmux target；确认后用 `sync --yes` 应用。

## 会话管理

### 列出会话

```bash
cc-branch session list
```

常见状态包括：

- `running`
- `stopped`
- `orphaned`

### 查看单条记录

```bash
cc-branch session inspect dev:planner
```

### 清理孤立记录

```bash
cc-branch session prune --dry-run
cc-branch session prune
```

### 输出恢复命令

```bash
cc-branch session command dev:planner
```

这个命令会优先返回已经解析好的 `launch_command`。

## Web UI

### 启动

```bash
cc-branch serve
cc-branch serve --host 127.0.0.1 --port 8080
cc-branch serve --host 0.0.0.0 --token "$CC_BRANCH_WEB_TOKEN"
```

`serve` 可以直接在没有 `.cc-branch/config.yaml` 的目录中启动。此时 Web UI 会显示 setup 流程，用户选择模板或保存 YAML 后才会写入配置文件。

如果配置了 token，第一次在浏览器打开时使用服务端打印的 `/?token=...` 链接。验证通过后，服务端会设置 HttpOnly cookie，后续访问根页面和所有 `/api/*` 请求都会使用这个 cookie。

### 现在可以做什么

- 查看状态
- 查看和保存配置
- 查看诊断结果
- 查看可用模板
- 初始化工作空间
- 用同一个工具选择器打开工作空间或项目目录
- 后台启动、重启、停止 tmux 工作空间或标签页

Web UI 中有一个工具选择器和两个主要动作：

- “打开工作空间”会按所选工具适配：Terminal.app、iTerm2 等终端会运行 dashboard/attach 命令；Warp 会写入稳定的 Launch Configuration 并打开一个布局；VS Code、Cursor 会正常打开项目目录，在 macOS 上还会通过本机 UI 自动化创建 integrated terminal 来运行对应命令。
- “打开项目目录”使用同一个所选工具，但只有工具支持 `open_project` 时才可点击。它不会启动或 attach workspace；终端类工具会在项目目录打开一个交互 shell，编辑器类工具会打开项目文件夹。
- Tab 或 pane 旁边的“打开”也使用同一个所选工具。Terminal/Warp 会直接运行 attach 或 direct-layout 命令；在 macOS 上，VS Code、Cursor 会正常打开项目目录，并创建 integrated terminal 运行该目标命令。

`layoutBackend: tmux` 是可复用的；即使之前已经在另一个 Terminal 或 Warp 窗口打开过，再次打开也会 attach 到同一组 tmux session。`layoutBackend: direct` 是外部进程，不能被复用或停止；再次打开会启动新的终端进程，需要用户手动关闭窗口。

VS Code 和 Cursor 的 integrated terminal 自动打开依赖 macOS Accessibility 权限。如果系统阻止自动化，请给运行 `cc-branch` 的终端或桌面应用授予辅助功能权限后重试。

Warp 通过 Launch Configuration 执行命令；当 opener 支持 layout 时，CC Branch 会把每个 tmux 标签页作为一个 attach 入口放进布局，标签页内部的多个 pane 由 tmux 自己管理和切换；direct 布局窗格会作为单独 pane 展开。如果想打开可见工作空间，使用“打开工作空间”或 `cc-branch open`。

### 额外说明

- 前端资源会随包一起提供
- 可以通过 `project_path` 切换目标项目
- 可以通过 `CC_BRANCH_CONFIG` 和 `CC_BRANCH_STATE` 覆盖默认路径
- 绑定到非本机地址时必须使用 `--token` 或 `CC_BRANCH_WEB_TOKEN`；token 模式会保护 Web UI 和所有 API

## Python API

如果你要把 CC Branch 接进自己的工具，也可以直接使用这些接口：

```python
from cc_branch import load_workspace, load_state, plan_workspace
from cc_branch import WorkspaceContext, WorkspaceConfig, WorkspacePlan, WorkspaceState
```

这样你可以直接复用配置装载、状态装载和计划生成逻辑，而不必自己重复实现一遍。

## 常见工作流

### 每天进入项目

```bash
cc-branch start
```

如果想在启动前确认会创建哪些 session/pane，可以先运行 `cc-branch plan`。

### 看看当前是否健康

```bash
cc-branch status
cc-branch session list
cc-branch doctor
```

### 清理旧记录

```bash
cc-branch session prune --dry-run
cc-branch session prune
```

### 用浏览器查看

```bash
cc-branch serve
```

如果你有多个项目，可以结合 `project_path` 切换不同目标。

如果当前目录还没有配置，Web UI 会进入初始化流程；不需要先在终端里运行 `cc-branch init`。

## 常见问题

### `tmux is required`

说明当前操作需要 `layoutBackend: tmux`，但当前环境里没有找到 `tmux`。如果不需要 tmux 的复用、后台生命周期或 attach 能力，把对应 tab 改成 `layoutBackend: direct` 即可。

### `unknown tab` / `unknown pane`

说明你传给 `attach`、`stop` 或 `restart` 的目标不在当前计划里。

### `missing session_id`

如果某个窗口依赖恢复信息，先运行：

```bash
cc-branch plan --write-state
```

### 找不到命令行工具

```bash
cc-branch doctor
```

先看具体缺的是哪个 `command`。

## 继续阅读

- `docs/features.md`
- `docs/architecture.md`
- `docs/webui-spec.md`

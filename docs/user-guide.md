# CC Branch 使用指南

这份文档面向已经准备开始使用 CC Branch 的用户。它重点解释怎么初始化、怎么配置、怎么日常操作，以及出了问题时先看哪里。

## 安装与环境

### 环境要求

- `tmux`
- 你会在配置里实际使用到的命令行工具
- 只有通过 PyPI 或源码安装时才需要 Python 3.10 或更高版本

Windows 下请通过 WSL、MSYS2 或 Cygwin 提供可用的 `tmux`。

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

- 检查 `tmux`
- 探测常见命令行工具
- 按模板生成起步配置
- 创建 `.cc-branch.state.toml`
- 在需要时补齐 `session_id`
- 更新 `.gitignore`

`solo-dev` 是默认模板；检测到可用 Agent CLI 时，session metadata 会自动初始化。只有在需要非默认模板时才加 `--profile`。

### 最简方式

```bash
cc-branch init --minimal
```

如果你已经知道自己要写什么配置，只想先拿到基础文件，可以用这个模式。

### 可选模板

```bash
cc-branch init --profile ai-pair
cc-branch init --profile minimal
```

## 配置文件和状态文件

### 配置文件查找顺序

1. `.cc-branch.yaml`
2. `.cc-branch.yml`
3. `.cc-branch.toml`

推荐优先使用 `.cc-branch.yaml`。

### 两个关键文件

- `.cc-branch.yaml`：项目配置，适合提交到仓库
- `.cc-branch.state.toml`：本地运行状态，通常不建议提交

状态文件里常见的信息包括：

- `session_id`
- `label`
- `agent`
- `slot`
- `window`

## 配置怎么写

### 顶层结构

```yaml
version: 1
project: "my-project"
root: "."

display:
  mode: "grid"
  columns: 2
  dashboard: true

agents: {}
slots: []
```

### `display`

- `mode`：总览面板的布局方式
- `columns`：`grid` 模式下的列数
- `dashboard`：旧配置字段；当前需要显式运行 `dashboard` 或 `start --dashboard` 进入总览面板

### `agents`

每个 agent 可以声明这些字段：

- `command`
- `resume_mode`
- `resume_template`
- `create_mode`
- `create_template`
- `label_template`
- `label_mode`
- `rename_template`

内置 agent：claude、codex、gemini、cursor、kimi。

如需添加自定义 agent，创建 `~/.cc-branch/agents.yaml`：

```yaml
agents:
  my-agent:
    command: my-agent
    resume_mode: flag
    resume_template: "--restore {session_id}"
```

可用模板变量：`{session_id}`、`{project}`、`{slot}`、`{window}`、`{label}`。

`resume_mode` 说明：

- `flag` — 启动时附加 flag（如 `codex resume <id>`）
- `internal` — 启动后发送 post-launch 命令恢复
- `none` — 不处理恢复，直接运行命令

### `slots`

每个 `slot` 在运行时都会对应一个 tmux 会话。

常见字段有：

- `name`
- `backend`
- `cwd`
- `env`
- `windows`
- `command`
- `window_name`
- `agent`
- `session_id`
- `label`

### `windows`

窗口层常见字段有：

- `name`
- `agent`
- `command`
- `cwd`
- `env`
- `session_id`
- `label`
- `label_template`
- `resume_mode`
- `resume_template`
- `create_mode`
- `create_template`
- `label_mode`
- `rename_template`

## 计划和运行时规则

### `shell` slot 会被归一化

```yaml
- name: "scratch"
  backend: "shell"
  command: "zsh"
```

这类写法在运行时会被整理成一个只包含 `main` 窗口的结构。

### 路径如何解析

- slot 的 `cwd` 相对于 `root`
- window 的 `cwd` 相对于 slot 的 `cwd`
- 绝对路径会保持不变

### 环境变量如何合并

- slot 的 `env` 和 window 的 `env` 会合并
- window 同名字段会覆盖 slot
- 最终会注入到实际启动命令前

### 创建和恢复如何处理

CC Branch 会根据配置和本地状态，生成最终 `launch_command` 与 `post_launch_commands`。

常见模式包括：

- `resume_mode = flag`
- `resume_mode = internal`
- `create_mode = generated_uuid`

## 常用命令

### `plan`

```bash
cc-branch plan [--write-state] [--bootstrap-if-missing] [--json]
```

适合在正式启动前先确认：

- 命令是否正确
- 目录是否正确
- `session_id` 是否已经准备好
- label 和附加命令是否符合预期

### `start`

```bash
cc-branch start [--prepare] [--bootstrap-if-missing] [--detach] [--dashboard]
```

它会创建 tmux 会话和窗口，并默认进入第一个 slot。只想后台启动时使用 `--detach`。

需要总览面板时，使用 `cc-branch dashboard` 或 `cc-branch start --dashboard`。`start` 不会因为 `display.dashboard` 配置而静默切换到面板。

### `status`

```bash
cc-branch status [--write-state] [--bootstrap-if-missing] [--json]
```

常见输出包括：

- slot 是否在运行
- window 是否存在
- 当前 `session_id`
- 当前 label
- agent 名称

### `attach`

```bash
cc-branch attach <slot>
cc-branch attach <slot>:<window>
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
cc-branch dashboard [--prepare] [--bootstrap-if-missing]
```

### `doctor`

```bash
cc-branch doctor [--write-state] [--bootstrap-if-missing] [--fix]
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

`serve` 可以直接在没有 `.cc-branch.yaml` 的目录中启动。此时 Web UI 会显示 setup 流程，用户选择模板或保存 YAML 后才会写入配置文件。

如果配置了 token，第一次在浏览器打开时使用服务端打印的 `/?token=...` 链接。验证通过后，服务端会设置 HttpOnly cookie，后续访问根页面和所有 `/api/*` 请求都会使用这个 cookie。

### 现在可以做什么

- 查看状态
- 查看和保存配置
- 查看诊断结果
- 查看可用模板
- 初始化工作空间
- 在本机系统终端打开 workspace dashboard 或某个 slot
- 在 VS Code、Cursor 等编辑器中打开项目目录
- 后台启动、重启、停止工作空间或 slot

Web UI 中的“在终端打开工作空间”会调用本机后端打开系统终端并运行 `cc-branch dashboard`。Open With 下拉可以选择可用 opener；VS Code 和 Cursor 这类编辑器 opener 只打开项目目录，不会自动 attach tmux。如果只想创建 tmux 会话但不弹出终端窗口，使用“后台启动”。

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

如果想在启动前确认会创建哪些 session/window，可以先运行 `cc-branch plan`。

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

说明当前环境里没有找到 `tmux`。

### `unknown slot` / `unknown window`

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
- `wiki/README.md`

# CC Branch 功能概览

CC Branch 是一个面向终端 AI 工作流的 CLI-first 工作空间编排器。它不替代 `tmux`，而是把工作空间的定义、启动、恢复、诊断和查看方式统一起来。

## 适合做什么

- **把工作空间写进配置**：用 `.cc-branch/config.yaml` 描述 workspace、tab、pane、agent、目录和环境变量。
- **用同一套命令管理全流程**：从 `init`、`plan`、`start` 到 `status`、`doctor`、`session`，入口保持一致。
- **让恢复更稳定**：把本地运行信息写进 `.cc-branch/state.yaml`，回到项目时更容易接上之前的会话。
- **看清并操作 Agent**：状态 payload 和 Web UI 会把 agent pane 汇总成 Agent 状态中心，显示位置、session、最近活动和可用操作。
- **给浏览器一层可视化入口**：除了 CLI，也可以通过内置 Web UI 查看状态、配置和诊断结果。

## 主要功能

### 配置驱动

工作空间结构放在 `.cc-branch/config.yaml` 里，团队可以共享同一份结构定义，本地运行状态则单独保存在 `.cc-branch/state.yaml`。

你可以在配置里描述：

- `agents` 覆盖，通常可省略，因为内置 agent profile 默认可用
- `tabs`
- `panes`
- `cwd`
- `env`
- `remote`
- `display`

### 启动前先预览

`cc-branch plan` 会先把最终结果算出来，再决定要不要启动。

它会帮你确认：

- 每个 tab 会对应哪个 tmux 会话或 direct 进程
- 每个 pane 最终会执行什么命令
- 哪些 pane 会通过本机 `ssh` 跑在远程服务器上
- 哪些 `session_id` 会复用，哪些会自动补齐
- 启动后还会执行哪些附加命令

### 启动与恢复

`cc-branch start` 负责把计划变成实际工作空间，`attach`、`stop`、`restart` 则负责后续操作。

对支持恢复的命令行工具，CC Branch 会结合配置和本地状态，生成更稳定的启动或恢复命令。

`cc-branch send <tab[:pane]> <message>` 可以把一条消息发送到正在运行的 tmux 托管窗格。Web UI 的 Agent 状态中心也使用同一条 action 路径发送消息。每次发送都会写入本机 Agent Bus 事件日志，状态中心会显示目标 Agent 的 inbox 未读数和最近消息，并可追加 read receipt 把未读消息标为已读。

### Agent 状态中心

`cc-branch status --format json` 会返回顶层 `agents` 列表。每个条目包含：

- agent 名称和 CLI
- local / SSH 位置
- cwd、tmux session/window
- session id、transcript path
- 最近活动摘要
- inbox 未读数和最近消息
- 可选 agent worktree branch、path 和 diff 计数
- busy、stale、stopped、error 等状态
- attach、send、restart、stop 等可用操作

### Workspace Snapshot

`cc-branch snapshot create` 会把当前 workspace 的配置引用、state、tabs/panes 运行状态、Agent session 绑定、SSH target、tmux session、最近状态和 git branch/worktree 信息保存到本机 `~/.cc-branch/app/snapshots.json`。Snapshot 是本地运行态，不会默认提交到项目 git。

常用命令：

- `cc-branch snapshot create --name before-refactor`
- `cc-branch snapshot create --name before-refactor --include-files`
- `cc-branch snapshot list`
- `cc-branch snapshot show <id-or-name>`
- `cc-branch snapshot preview <id-or-name>`
- `cc-branch snapshot restore <id-or-name>`
- `cc-branch snapshot restore <id-or-name> --dry-run`
- `cc-branch snapshot restore <id-or-name> --state-only`
- `cc-branch snapshot export <id-or-name> --output snapshot.json`
- `cc-branch snapshot import snapshot.json --name restored-copy`

Web UI Dashboard 顶部也提供保存快照按钮。默认 snapshot 保存运行态；加 `--include-files` 时还会捕获工作区文件内容，恢复时会把文件改回快照时的状态，删除快照之后新增的文件，并恢复被删除或修改的文件。文件快照会跳过 `.git`、`.cc-branch/app`、`node_modules`、构建目录和虚拟环境等重目录，单文件默认上限 2MB，总量默认上限 50MB；它适合做本地小型时间机器，不替代 git、备份系统或远程文件同步。`--state-only` 可只恢复 session/runtime metadata。

恢复 snapshot 会把保存的 session/runtime metadata 写回对应 `state.yaml`，之后可以继续用 `cc-branch start` 或 Web UI 恢复工作现场。`preview` 和 `--dry-run` 会先对比当前 `state.yaml` 与 snapshot 里的 windows/slots/files，显示将新增、删除、改变或保持不变的记录；`export/import` 用于把某个本地运行现场复制到另一台机器或归档。

### Worktree Per Agent

`cc-branch worktree setup <tab[:pane]>` 可以为单个 Agent 创建可选 git worktree 和 branch，用于并行开发而不污染主工作区。第一版覆盖：

- 创建或导入 agent worktree
- 为 agent 显示 branch、path、dirty 状态和 changed file 计数
- Web UI 工作空间配置页可把 agent pane 的工作目录切到已检测到的 worktree
- 复制或软链指定 gitignored 文件，例如 `.env`
- setup hook
- finish/status/cleanup 的本地 lifecycle
- 同一 repo 下 setup/cleanup 操作会用本地 lock 串行化

常用命令：

- `cc-branch worktree setup dev:planner --branch cc-branch/dev-planner --copy .env`
- `cc-branch worktree status`
- `cc-branch worktree finish dev:planner`
- `cc-branch worktree import dev:planner ../planner-worktree`
- `cc-branch worktree cleanup dev:planner`

### 会话管理

`session` 子命令把会话元数据当成单独对象来管理，而不只是附着在 `status` 输出里。

目前可用的子命令包括：

- `session list`
- `session inspect`
- `session prune`
- `session command`
- `session restore`
- `session hook`

这对于长期项目尤其有用，因为你可以更清楚地区分正在运行、已经停止和已经孤立的记录。

`session restore` 会扫描本机 Codex、Claude、Gemini、Cursor、Kimi 等 Agent 的 transcript/session 文件，把匹配当前项目和 Agent 的 session 绑定回 `.cc-branch/state.yaml`。默认只扫描当前项目目录相关 session；需要从其它项目找回 session 时，可用 `--session-scope all` 扩展到全部本机已知 session。它支持 `--dry-run`、`--target dev:planner`、`--agent claude`、`--session-id <id>`、`--session-scope project|all` 和 `--force`，会返回候选 session、计划绑定、选择来源和跳过原因。Web UI 的 session picker 同样默认显示当前项目，并提供“全部项目”切换。

Dashboard 会把 Agent 的实时状态、最近活动、未读消息和 worktree 状态直接合并到对应的 workspace pane/window 卡片里，而不是在布局上方再展示一个独立 Agent 状态面板。`session hook` 是给 agent-native hook 使用的轻量写回入口。Agent pane 启动时会带上 `CC_BRANCH_SESSION_TARGET`、`CC_BRANCH_SESSION_KEY`、`CC_BRANCH_AGENT`、`CC_BRANCH_PROJECT_DIR` 等环境变量；Codex、Claude 等工具自己的 hook 可以在拿到真实 session id 或 transcript 路径后调用 `cc-branch session hook`，把会话绑定回 `.cc-branch/state.yaml`。下一次打开 workspace 时，CC Branch 会优先复用这个绑定生成恢复命令。

### 诊断与自动修复

`cc-branch doctor` 用来检查当前环境和配置是否健康，`doctor --fix` 会尝试处理其中一部分低风险问题。

常见检查包括：

- `tmux` 是否可用
- 配置里的命令是否存在
- 远程 pane 所需的本机 `ssh` 是否存在
- 远程 pane 的 SSH 目标是否可达，远端 `cwd`、`tmux` 和命令是否存在
- `cwd` 是否存在
- agent 名称是否可识别
- 需要恢复的窗格是否缺少 `session_id`

### 内置 Web UI

`cc-branch serve` 会启动一个轻量服务，提供浏览器里的查看入口。

它适合用来：

- 查看工作空间状态
- 查看 Agent 状态中心并向正在运行的 agent pane 发送消息
- 查看或保存配置
- 查看诊断结果
- 使用内置模板初始化项目
- 使用同一个工具选择器打开工作空间或项目目录
- 适配系统终端、Warp、VS Code、Cursor 等本机工具
- 显式配置工作空间画布的 `n x m` 网格，并在 Warp Launch Configuration 中按该行列布局打开
- 后台启动、重启、停止 tmux 工作空间或标签页

### 可集成

CC Branch 不只是一个 CLI。当前包也导出了带类型的 Python API，方便桌面包装层、自动化脚本或其他工具直接复用配置装载和计划生成能力。

## 常见使用方式

### 单人开发工作台

一个项目里同时放 UI、API、QA、文档、评估等窗格，减少来回手动搭环境的时间。

### 双人或双角色协作

用 `development`、`research`、`minimal` 三种模板按工作形态快速起步，避免一开始就让用户理解内部配置结构。

### 长期项目

当项目会持续很多天甚至更久时，本地状态和 `session` 管理会明显更有价值，因为你不需要每次都从头整理现场。

### 多项目查看

通过 Web UI 的 `project_path` 覆盖能力，可以把多个项目接到同一套查看入口里。

## 当前重点

现在的产品重点很明确：

- 以 CLI 为主入口
- 以 direct 和 tmux 两种布局承载方式为运行基础
- 通过 `remote` 支持把部分工作负载交给 SSH 服务器执行
- 以配置文件和本地状态文件作为统一数据源
- 以 session 管理和诊断能力补上长期使用体验

## 当前边界

如果你在评估是否适合自己的流程，下面这些边界也很重要：

- tmux 提供最完整的后台生命周期、attach、stop/restart 和 sync 能力
- direct 布局适合普通本地 shell/editor 进程，但不具备 tmux 的可复用生命周期
- SSH remote 负责远程执行命令，但不负责远程文件同步或密钥管理
- Web UI 已经可用，但它不是独立运行时，只是另一层查看和操作入口
- Wiki 里的旧评审或阶段文档不一定代表当前行为，公开说明以 `docs/` 为准

## 继续阅读

- `docs/getting-started.md`
- `docs/quickstart.md`
- `docs/user-guide.md`
- `docs/architecture.md`

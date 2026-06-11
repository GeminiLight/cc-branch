<!-- Last verified: 2026-06-11 | Current stage: product planning -->

# CC Branch Features Overview

这份文档整理 CC Branch 接下来值得做的功能方向。判断标准不是“还有什么能加”，而是这些功能能不能让 CC Branch 更像一个开发者每天会打开的多 Agent CLI 工作台。

## 产品定位

CC Branch 是多 Agent CLI 项目的工作台和恢复层。

它不替代 Codex、Claude Code、Gemini CLI，也不替代 tmux、SSH、Cursor 或 VS Code。它负责把一个项目需要的 Agent、终端、编辑器、本地目录、SSH 机器和可复用 session 组织起来，并在用户回来时一键恢复。

下一阶段的重点应该从“恢复终端布局”升级到“接回多 Agent 工作现场”。

## 核心用户价值

### 1. 一键恢复多 Agent 工作环境

用户的真实工作台通常不止一个终端：可能有 Codex、Claude Code、dev server、日志窗口、tmux session、远程 GPU 机器和本地编辑器。

CC Branch 要让用户配置一次，之后每次回到项目都能直接恢复，不需要重新开窗口、重新 cd、重新 ssh、重新找 session。

### 2. 看清每个 Agent 的状态

多 Agent 工作流的麻烦不只是“窗口多”，而是用户不知道谁在跑、谁卡住、谁有新输出、谁已经可以继续。

CC Branch 应该提供一个状态中心，让用户一眼看到每个 Agent 的 CLI、目录、机器、session、最近输出、运行状态和可操作入口。

### 3. 在本地和远程之间统一工作

很多项目不会只在本机跑：代码在本地，训练或评估在 SSH 机器，某些 Agent 在远程 tmux 里，编辑器还在本地。

CC Branch 应该把 local 和 SSH 当作同一个 workspace 的两种执行位置，而不是两个割裂的世界。

## 功能路线

### P0: Agent 状态中心

目标：把“打开了一堆终端”变成“管理一组可识别的 Agent”。

应该展示：

- Agent 名称
- Agent CLI，例如 Codex、Claude Code、Gemini CLI、自定义命令
- local / SSH 位置
- cwd
- tmux session / pane
- session id / transcript path
- 最近输出摘要
- busy / idle / stopped / stale / error 状态
- attach、send、restart、stop 操作

用户价值：

- 回到项目时不用先挨个终端确认状态。
- 多 Agent 同时工作时，用户知道该看谁、接谁、重启谁。
- 桌面端和 Web UI 会有明确的主界面，而不是只显示配置和诊断。

实现边界：

- 先基于现有 state、tmux、session hook 和 status 能力实现。
- 不需要一开始做完整任务看板。
- “最近输出”可以先从 tmux capture-pane 或 transcript path 读取。

### P0: 跨 Agent 发送消息

目标：用户可以从 CC Branch 给任意 Agent 发一条消息。

典型操作：

```text
发给 reviewer: 看一下 planner 的方案，重点检查有没有实现风险。
发给 qa: 跑一下回归测试，失败的话只汇总最关键的错误。
发给 remote-eval: 用当前分支在 GPU 机器上跑一次评估。
```

用户价值：

- 用户不需要切到具体终端再复制粘贴。
- 多 Agent 协作会从“多个窗口并排”变成“可以调度的工作台”。
- 这是 CC Branch 和普通 tmux/workspace 管理器拉开差距的关键功能。

实现边界：

- 第一阶段支持 tmux pane paste / direct process message。
- 第二阶段接 agent-native hook，把真实 session id 和 transcript 绑定起来。
- 第三阶段再考虑 inbox/outbox、event log 和跨机器消息。

### P0: 更强的 Session Restore

目标：恢复的不只是 pane，而是 Agent 的工作现场。

应该保存和恢复：

- Agent 名称
- Agent profile
- cwd
- local / SSH target
- tmux session / pane
- session id
- transcript path
- last status
- last command
- last attached time

用户价值：

- 回到长期项目时更像“继续工作”，而不是“重新启动工具”。
- 对 Codex、Claude Code 这类有 session 概念的工具，恢复体验会明显提升。
- desktop/Web UI 可以展示更可靠的历史和当前状态。

实现边界：

- 继续保留配置和运行态分离。
- 项目结构放 `.cc-branch/config.yaml`。
- 全局索引、跨项目 registry、运行记录可以放 `~/.cc-branch/`。

### P1: SSH 远程项目添加

目标：Add Project 不只支持本地目录，也支持 SSH 机器上的目录。

应该支持：

- 选择或输入 SSH host
- 输入远程 cwd
- 检查远程路径是否存在
- 检查远程 tmux 是否可用
- 检查远程 Agent CLI 是否存在
- 保存为项目 workspace
- 从桌面端/Web UI 一键打开或恢复

用户价值：

- 远程机器会成为 CC Branch 的核心能力，而不是配置文件里的高级用法。
- GPU box、远程 dev server、公司跳板机等场景更自然。
- 多 Agent 项目经常跨机器，这个能力会很有辨识度。

实现边界：

- 不做远程文件同步。
- 不管理 SSH key。
- 只负责连接、检查、启动、恢复和状态展示。

### P1: Workspace Snapshot

目标：用户可以保存当前工作现场，并在之后恢复。

Snapshot 应包含：

- 当前 workspace 配置引用
- 运行中的 tabs / panes
- Agent session 绑定
- SSH target
- tmux session
- 最近状态
- 当前分支或 worktree 信息

用户价值：

- 用户不必理解配置细节，也能保存“现在这个状态”。
- 长期项目、临时实验、多分支并行都会更稳。
- Snapshot 可以成为 desktop app 里的高频按钮。

实现边界：

- Snapshot 是本地运行态，不应默认提交 git。
- 可以支持导出，但默认保存在 `~/.cc-branch/` 或项目 state。

### P1: 高质量工作流模板

目标：让用户第一次用就能理解 CC Branch 的使用方式。

建议模板：

- `single-agent`: 一个 Agent + 编辑器 + dev server
- `codex-claude-review`: Codex 实现，Claude Code review
- `planner-implementer-reviewer`: 规划、实现、审查三 Agent
- `local-remote-lab`: 本地开发 + SSH 评估机器
- `docs-dev-qa`: 文档、开发、测试并行

用户价值：

- 降低第一次配置成本。
- 官网和 README 可以用模板解释产品价值。
- 用户会更快把 CC Branch 套进自己的工作流。

实现边界：

- 模板必须能直接运行或只需少量修改。
- 不要把模板写成抽象 demo，要对应真实开发场景。

### P2: Worktree Per Agent

目标：给每个 Agent 自动创建独立 git worktree 和 branch，降低并行修改冲突。

用户价值：

- 多 Agent 可以并行做不同任务，不互相污染工作区。
- UI 可以展示每个 Agent 的 branch、diff、改动数量。
- 适合长期复杂项目。

实现边界：

- 这会改变用户 Git 工作流，必须可选。
- 需要清晰的 cleanup、merge、discard、open diff 操作。
- 不应该成为初始配置的默认复杂度。

### P2: 可选 Memory / MCP 集成

目标：恢复工作环境时，也能恢复项目上下文。

可以支持：

- 启动前读取 external memory 的 recent activity
- 把 session snapshot 写成 checkpoint
- 在 Agent 启动 prompt 里注入 project brief
- 支持 Basic Memory、Guild 或自定义 MCP memory provider

用户价值：

- 用户不只恢复终端，还能恢复“昨天做到哪儿”。
- 多 Agent 可以共享项目决策、交接摘要和最近上下文。

实现边界：

- CC Branch 不应该内置完整知识库。
- Memory provider 应该是可选集成。
- 默认路径仍然是本地 workspace restore。

## 建议的 MVP 顺序

1. Agent 状态中心
2. 跨 Agent 发送消息
3. 更强的 session restore
4. SSH 远程项目添加
5. Workspace snapshot
6. 工作流模板
7. Worktree per Agent
8. 可选 Memory / MCP 集成

这个顺序的原因很简单：前 4 个功能直接强化 CC Branch 的核心定位；后 4 个功能能扩大使用场景，但不应该先把产品做重。

## 不建议优先做

- 完整任务看板
- PR review 平台
- 云端多用户协作
- 内置知识库
- 自研 Agent runtime
- 强制 worktree 工作流
- 默认跨设备消息 relay

这些功能不是没有价值，而是会把 CC Branch 从“多 Agent CLI 工作台”带向另一个产品形态。现阶段更应该把本地/SSH、多 Agent、session 恢复和状态可视化做到足够顺。

## 判断标准

每个新功能进入实现前，都应该问四个问题：

1. 它是否让用户更快回到项目现场？
2. 它是否减少了多 Agent CLI 的窗口、session、SSH、目录管理成本？
3. 它是否能和现有配置、state、tmux、SSH 模型自然结合？
4. 它是否避免把 CC Branch 变成任务管理器、知识库或另一个 Agent？

如果答案大多是 yes，就值得做。否则应该先放到 backlog。

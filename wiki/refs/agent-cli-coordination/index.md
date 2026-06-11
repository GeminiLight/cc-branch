<!-- Last verified: 2026-06-11 | Current stage: reference research -->

# Agent CLI 协同与跨终端通信调研

这份资料调研了 12 个开源项目，重点看它们如何让多个 Agent CLI、多个终端会话、多个工作树或共享记忆层协同工作。调研不是为了做功能堆叠，而是为了帮助 CC Branch 判断：哪些能力应该成为项目工作台的一部分，哪些能力应该保持为可选集成。

## 调研对象

| 项目 | 类型 | 一句话定位 | 与 CC Branch 的关系 |
|---|---|---|---|
| [hcom](./hcom.md) | 跨终端消息层 | 用 hook、SQLite 和终端观察能力连接多个 Agent CLI | 最接近“跨 Terminal Agent Bus”的参考 |
| [guild](./guild.md) | 记忆与任务协调 | 本地 SQLite + MCP 的共享任务、知识、交接层 | 可参考它的任务领取和会话交接模型 |
| [wit](./wit.md) | 协调协议 | 用 intent、symbol lock、contract 提前暴露冲突 | 可参考“启动前检查”和语义级锁 |
| [swarm-protocol](./swarm-protocol.md) | 团队状态协议 | PostgreSQL + MCP 的 intent/claim/signal/context 协议 | 可参考它的共享状态词汇，但不必照搬服务端依赖 |
| [gnap](./gnap.md) | Git-native 协议 | 用 `.gnap/` JSON 文件和 git 作为 Agent 协调层 | 可参考“配置即协议”和审计日志思路 |
| [claude-squad](./claude-squad.md) | 终端运行层 | tmux + git worktree 管理多个 AI 终端实例 | 与 CC Branch 的终端恢复、分支隔离高度相关 |
| [vibe-kanban](./vibe-kanban.md) | Agent 工作台 | 看板、工作树、终端、预览和 diff 审查的一体化工作台 | 可参考任务执行视图，不建议照搬完整 PM 系统 |
| [agent-kanban](./agent-kanban.md) | Agent 看板/队列 | task board + daemon + worker agents + 身份权限 | 可参考 Agent 身份、任务状态和事件总线 |
| [ORCH](./orch.md) | CLI 编排器 | 用 TUI/CLI 管理多 Agent、任务、消息和共享上下文 | 可参考消息 fanout 与 pending mailbox |
| [tutti](./tutti.md) | Agent Ops | 用 `tutti.toml` 声明角色、运行时、hook、gate 和 dashboard | 可参考“Agent ops as code” |
| [shire](./shire.md) | Agent 宿主环境 | Bun/Hono/SQLite/Web UI 管理持久 Agent、outbox 消息和 shared drive | 可参考 outbox/inbox 文件通信和 shared drive |
| [basic-memory](./basic-memory.md) | 共享记忆层 | Markdown 笔记 + 知识图谱 + MCP + 插件化 checkpoint | 可参考跨 Agent 记忆、session brief、pre-compact checkpoint |

## 三层问题

### 1. 终端与进程层

这一层解决“Agent CLI 跑在哪里、如何恢复、如何观察和输入”的问题。典型方案有：

- `tmux` 会话：`claude-squad`、`tutti` 把每个 Agent 放进独立 tmux session/pane，适合恢复、捕获输出、批量操作。
- SDK/harness 进程：`shire` 不以终端为中心，而是用 Claude Code、Codex、OpenCode、Pi Agent 的 SDK 或 harness 收发消息。
- hook 包装启动：`hcom` 通过 `hcom claude`、`hcom codex` 等包装 Agent CLI，把 hook 和本地 DB 接进原有终端。

对 CC Branch 来说，这一层是核心。CC Branch 已经在做 workspace/tab/pane 和 tmux-backed session，下一步如果要做跨 Agent 协同，应该优先扩展现有运行层，而不是先引入大型看板或服务端。

### 2. 消息与事件层

这一层解决“Agent 如何互相知道对方在做什么、如何发消息、如何订阅事件”的问题。不同项目的取舍很明显：

- SQLite event log：`hcom` 用本地 SQLite 记录消息、终端观察、编辑事件，再由 hook 注入或唤醒目标 Agent。
- 文件 outbox/inbox：`shire` 让 Agent 写 YAML 到自己的 `outbox/`，Coordinator 监听后路由到目标 Agent。
- MCP tools：`guild`、`swarm-protocol`、`basic-memory` 把状态读写暴露成 MCP 工具，让不同客户端通过同一协议接入。
- Git JSON 文件：`gnap` 把 Agent、task、run、message 全放进 `.gnap/`，用 git pull/push 同步。
- TUI 内部队列：`ORCH` 用 MessageService 处理 direct、broadcast、lead channel，并在派发任务时把 pending mailbox 注入 prompt。

CC Branch 可以先做轻量的“Agent Bus”：事件日志、Agent inbox、终端状态、消息发送、最近活动。它不需要一开始就做复杂权限、团队看板或云同步。

### 3. 记忆与上下文层

这一层解决“多 Agent 如何共享长期上下文、决策、任务进度和交接”的问题。典型模式：

- 结构化本地记忆：`guild` 的 Quest/Lore/Oath/Brief 把任务、知识、规则、交接分开。
- Markdown 知识库：`basic-memory` 把 Markdown 作为源文件，用数据库索引 observations、relations、permalink 和全文/语义搜索。
- 协调状态：`wit`、`swarm-protocol` 用 intent、claim、lock、contract、signal 等概念让 Agent 在开工前互相避让。
- 运行交接：`ORCH`、`tutti` 更关注任务执行记录、session memory、run ledger 和 review gate。

CC Branch 当前最适合做的是“工作环境恢复 + 可选记忆集成”。共享记忆可以通过 MCP 或插件接入，不必直接变成 CC Branch 自己的知识库产品。

## 架构模式对比

| 模式 | 代表项目 | 优点 | 代价 |
|---|---|---|---|
| 本地 SQLite + hook | hcom | 低部署成本，可记录事件、状态和消息 | 需要适配各 Agent CLI hook/输出习惯 |
| tmux + worktree | claude-squad, tutti | 终端恢复直观，隔离冲突，容易落地 | 跨平台和非 tmux 用户体验要额外处理 |
| MCP + 本地 DB | guild, basic-memory | 对多 Agent 客户端友好，能力可被调用 | 需要用户配置 MCP，实时性通常靠轮询或工具调用 |
| daemon + Unix socket/API | wit, shire | 状态集中，UI 和 Agent 都好接入 | 多一个后台进程，生命周期管理变复杂 |
| Git-native JSON 协议 | gnap | 零服务端、可审计、离线友好 | 实时性弱，冲突处理依赖 git 纪律 |
| 云/服务端看板 | agent-kanban, vibe-kanban | 适合多人、任务队列、PR 审查和监控 | 产品边界大，容易偏离“CLI 工作台” |

## 对 CC Branch 的建议

### 可以优先吸收

- **项目级全局目录**：继续把 `.cc-branch/config.yaml` 作为项目配置，同时用 `~/.cc-branch/` 存全局索引、注册表和跨项目状态。项目运行状态仍应避免提交到 git。
- **轻量 Agent Bus**：在现有 workspace/pane 模型旁增加 `events`、`inbox`、`messages`、`terminal_snapshot` 等概念，先做本机跨终端协同。
- **终端恢复 + 消息恢复一起设计**：恢复 workspace 时，不只恢复 pane，也恢复 Agent 名称、目标目录、最近消息、最后一次状态。
- **doctor 检查扩展**：借鉴 `wit` 和 `hcom`，检查 Agent CLI 是否存在、路径是否有效、SSH 是否可达、tmux session 是否陈旧、多个 Agent 是否会编辑同一路径。
- **MCP 作为集成面**：长期记忆、团队知识库、任务协调可以先通过 MCP 接入，而不是全部内置。

### 暂时不建议照搬

- 不要一开始做完整看板、任务管理、PR review 系统。`vibe-kanban` 和 `agent-kanban` 的范围比 CC Branch 大很多。
- 不要把跨设备消息作为第一优先级。`hcom` 的 MQTT relay 很有价值，但安全边界和密钥管理会显著抬高复杂度。
- 不要把共享记忆做成唯一入口。开发者可能已经在用 Basic Memory、Obsidian、项目 wiki 或公司知识库，CC Branch 更适合做连接层。

## 建议的最小产品切面

1. **Workspace restore**：从配置恢复 local/SSH/tmux/direct 的多 Agent 工作环境。
2. **Agent registry**：知道每个 Agent 的名字、CLI、目录、pane/session、状态。
3. **Message send**：允许用户或 Agent 给某个 Agent 发一条消息，先支持本机和 tmux pane。
4. **Activity view**：展示每个 Agent 的最近输出、运行状态、错误和未读消息。
5. **Health check**：检查 Agent CLI、SSH、路径、tmux、配置和陈旧状态。

这条路径能保持 CC Branch 的定位：它不是新的 Agent，也不是新的知识库，而是多 Agent CLI 的工作台和恢复层。

## 资料来源

本目录下每个项目文件都记录了源仓库、调研日期、commit 快照和主要阅读文件。调研基于 2026-06-11 本地浅克隆的仓库内容，并用 GitHub 元数据做了二次校验。

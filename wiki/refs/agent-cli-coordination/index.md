<!-- Last verified: 2026-06-12 | Current stage: reference research -->

# Agent CLI 协同与跨终端通信调研

这份资料调研了 19 个开源项目，重点看它们如何让多个 Agent CLI、多个终端会话、多个工作树或共享记忆层协同工作。调研不是为了做功能堆叠，而是为了帮助 CC Branch 判断：哪些能力应该成为项目工作台的一部分，哪些能力应该保持为可选集成。

## 总数与结论

截至 2026-06-12，这轮调研共纳入 **19 个开源项目**：

- **强 worktree 相关**：10 个，重点研究“每个 Agent 一个 branch/worktree、终端/GUI 绑定、diff、merge、cleanup”。
- **终端/session 协调相关**：4 个，重点研究跨 terminal 消息、tmux/session 恢复、状态检测。
- **协议/记忆/任务协调相关**：5 个，重点研究 intent、claim、共享上下文、MCP、Git-native 协作。

最值得 CC Branch 优先吸收的不是完整看板，而是 **Worktree per Agent + Session Restore + Agent Status + Send Message + Merge/Cleanup** 这一条主线。

## 调研对象

| 项目 | 类型 | 一句话定位 | 与 CC Branch 的关系 |
|---|---|---|---|
| [vibe-kanban](./vibe-kanban.md) | Agent 工作台 | 看板、工作树、终端、预览和 diff 审查的一体化工作台 | 可参考任务执行视图，不建议照搬完整 PM 系统 |
| [claude-squad](./claude-squad.md) | 终端运行层 | tmux + git worktree 管理多个 AI 终端实例 | 与 CC Branch 的终端恢复、分支隔离高度相关 |
| [agent-deck](./agent-deck.md) | 终端 session manager | 多 AI CLI session、worktree、fork、conductor、watcher、Docker sandbox | 可参考 worktree finish/cleanup、session fork、hook/inbox |
| [Agent of Empires](./agent-of-empires.md) | TUI/Web session manager | tmux-backed session + worktree + Web dashboard + ACP 结构化视图 | 可参考 hook+scan 恢复、状态检测、Web 控制面 |
| [workmux](./workmux.md) | Worktree workflow | git worktree + tmux/zellij/kitty/WezTerm 窗口生命周期工具 | 可参考 create/open/merge/remove 的完整生命周期 |
| [Parallel Code](./parallel-code.md) | 桌面 Agent 工作台 | Electron GUI 中每个 task 一个 branch/worktree/agent/diff | 可参考 GUI task/worktree 模型和 worktree lock |
| [TermCanvas](./termcanvas.md) | 空间终端画布 | Project -> Worktree -> Terminal 无限画布与 hook telemetry | 可参考 Workspace GUI 层级、自由布局和状态信号 |
| [dux](./dux.md) | 轻量 TUI | 多个 PTY Agent 并排运行，每个 agent 一个 worktree | 可参考 provider/resume_args、companion terminal、startup command |
| [VibeTree](./vibe-tree.md) | 桌面/Web worktree app | Claude + 多 git worktree + persistent terminal + Web/mobile access | 形态参考，成熟度低于前几项 |
| [hcom](./hcom.md) | 跨终端消息层 | 用 hook、SQLite 和终端观察能力连接多个 Agent CLI | 最接近“跨 Terminal Agent Bus”的参考 |
| [guild](./guild.md) | 记忆与任务协调 | 本地 SQLite + MCP 的共享任务、知识、交接层 | 可参考它的任务领取和会话交接模型 |
| [wit](./wit.md) | 协调协议 | 用 intent、symbol lock、contract 提前暴露冲突 | 可参考“启动前检查”和语义级锁 |
| [swarm-protocol](./swarm-protocol.md) | 团队状态协议 | PostgreSQL + MCP 的 intent/claim/signal/context 协议 | 可参考它的共享状态词汇，但不必照搬服务端依赖 |
| [gnap](./gnap.md) | Git-native 协议 | 用 `.gnap/` JSON 文件和 git 作为 Agent 协调层 | 可参考“配置即协议”和审计日志思路 |
| [agent-kanban](./agent-kanban.md) | Agent 看板/队列 | task board + daemon + worker agents + 身份权限 | 可参考 Agent 身份、任务状态和事件总线 |
| [ORCH](./orch.md) | CLI 编排器 | 用 TUI/CLI 管理多 Agent、任务、消息和共享上下文 | 可参考消息 fanout 与 pending mailbox |
| [tutti](./tutti.md) | Agent Ops | 用 `tutti.toml` 声明角色、运行时、hook、gate 和 dashboard | 可参考“Agent ops as code” |
| [shire](./shire.md) | Agent 宿主环境 | Bun/Hono/SQLite/Web UI 管理持久 Agent、outbox 消息和 shared drive | 可参考 outbox/inbox 文件通信和 shared drive |
| [basic-memory](./basic-memory.md) | 共享记忆层 | Markdown 笔记 + 知识图谱 + MCP + 插件化 checkpoint | 可参考跨 Agent 记忆、session brief、pre-compact checkpoint |

## GitHub 活跃度快照

GitHub 元数据通过 `gh repo view` 于 2026-06-12 查询。stars 会继续变化，这张表只用于判断当前优先级。

| 项目 | Stars | 最近 push | 创建时间 | 相关性判断 |
|---|---:|---|---|---|
| vibe-kanban | 26,933 | 2026-04-24 | 2025-06-14 | 高星、高相关，完整 Agent workbench |
| claude-squad | 7,775 | 2026-05-18 | 2025-03-09 | 高星、高相关，tmux + worktree TUI |
| basic-memory | 3,191 | 2026-06-11 | 2024-12-02 | 高星，偏记忆层 |
| agent-deck | 2,685 | 2026-06-11 | 2025-12-03 | 高相关，session/worktree/fork/hook 很完整 |
| Agent of Empires | 2,559 | 2026-06-11 | 2026-01-09 | 高相关，TUI/Web/session/status/worktree |
| workmux | 1,614 | 2026-06-06 | 2025-11-04 | 高相关，worktree 生命周期最完整 |
| Parallel Code | 715 | 2026-06-10 | 2026-02-18 | 高相关，GUI task/worktree/diff 模型 |
| agent-kanban | 341 | 2026-06-11 | 2026-03-20 | 中高相关，任务队列/worker/worktree |
| hcom | 337 | 2026-06-10 | 2025-07-21 | 高相关，跨 terminal hook/message bus |
| TermCanvas | 321 | 2026-05-31 | 2026-03-14 | 高相关，Project/Worktree/Terminal 画布 |
| guild | 310 | 2026-06-08 | 2026-04-20 | 中相关，共享上下文/MCP |
| VibeTree | 259 | 2026-01-02 | 2025-07-29 | 中相关，早期桌面/Web worktree app |
| ORCH | 76 | 2026-05-19 | 2026-03-10 | 中相关，消息与任务编排 |
| GNAP | 66 | 2026-03-17 | 2026-03-12 | 中相关，Git-native 协议 |
| dux | 53 | 2026-06-11 | 2026-03-22 | 高相关但早期，轻量 PTY/worktree TUI |
| swarm-protocol | 46 | 2026-03-15 | 2026-03-13 | 中相关，协议词汇 |
| wit | 43 | 2026-03-27 | 2026-03-26 | 中相关，intent/lock |
| tutti | 38 | 2026-05-05 | 2026-03-12 | 中相关，Agent Ops as code |
| shire | 32 | 2026-05-03 | 2026-03-17 | 中相关，agent host/outbox |

## 三层问题

### 1. 终端与进程层

这一层解决“Agent CLI 跑在哪里、如何恢复、如何观察和输入”的问题。典型方案有：

- `tmux` 会话：`claude-squad`、`Agent of Empires`、`agent-deck`、`workmux`、`tutti` 把每个 Agent 放进独立 tmux session/pane，适合恢复、捕获输出、批量操作。
- PTY 进程：`Parallel Code`、`dux`、`TermCanvas` 用 app 自己的 PTY runtime 管理 agent terminal，适合 GUI 直接控制。
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
- hook/telemetry：`Agent of Empires`、`TermCanvas` 用 CLI hook、session file scan、process/git watcher 等多信号推导 agent 状态。

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
| tmux + worktree | claude-squad, agent-deck, Agent of Empires, workmux, tutti | 终端恢复直观，隔离冲突，容易落地 | 跨平台和非 tmux 用户体验要额外处理 |
| GUI PTY + worktree | Parallel Code, dux, TermCanvas, VibeTree | 不依赖外部 tmux，适合桌面/画布交互 | 需要自己处理 PTY、session、进程恢复和渲染 |
| MCP + 本地 DB | guild, basic-memory | 对多 Agent 客户端友好，能力可被调用 | 需要用户配置 MCP，实时性通常靠轮询或工具调用 |
| daemon + Unix socket/API | wit, shire | 状态集中，UI 和 Agent 都好接入 | 多一个后台进程，生命周期管理变复杂 |
| Git-native JSON 协议 | gnap | 零服务端、可审计、离线友好 | 实时性弱，冲突处理依赖 git 纪律 |
| 云/服务端看板 | agent-kanban, vibe-kanban | 适合多人、任务队列、PR 审查和监控 | 产品边界大，容易偏离“CLI 工作台” |

## Worktree per Agent 模式总结

高相关项目基本都收敛到同一个模型：

```text
agent task/session
  -> branch
  -> git worktree
  -> terminal/PTY/tmux session
  -> agent CLI process
  -> diff/status/review
  -> finish: merge/rebase/squash + cleanup
```

成熟项目额外处理五个细节：

- **文件可用性**：复制 `.env`、`.mcp.json`、secrets，或 symlink `node_modules`、cache。
- **setup hook**：在 worktree 创建后运行 install/migration/direnv 等命令。
- **状态恢复**：记录 session id、provider、cwd、branch、worktree path、last status。
- **并发安全**：同一 repo 下 `git worktree add/remove` 串行化，避免 Git metadata 竞争。
- **收尾动作**：merge、remove、cleanup orphan、delete branch、close terminal/window。

## 对 CC Branch 的建议

### 可以优先吸收

- **项目级全局目录**：继续把 `.cc-branch/config.yaml` 作为项目配置，同时用 `~/.cc-branch/` 存全局索引、注册表和跨项目状态。项目运行状态仍应避免提交到 git。
- **轻量 Agent Bus**：在现有 workspace/pane 模型旁增加 `events`、`inbox`、`messages`、`terminal_snapshot` 等概念，先做本机跨终端协同。
- **终端恢复 + 消息恢复一起设计**：恢复 workspace 时，不只恢复 pane，也恢复 Agent 名称、目标目录、最近消息、最后一次状态。
- **doctor 检查扩展**：借鉴 `wit` 和 `hcom`，检查 Agent CLI 是否存在、路径是否有效、SSH 是否可达、tmux session 是否陈旧、多个 Agent 是否会编辑同一路径。
- **MCP 作为集成面**：长期记忆、团队知识库、任务协调可以先通过 MCP 接入，而不是全部内置。
- **可选 Worktree per Agent**：借鉴 `workmux`、`agent-deck`、`Parallel Code`，先做可选创建/导入/finish/cleanup，不要默认强制改变 Git 工作流。

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
6. **Optional worktree lifecycle**：为选中的 Agent 创建/导入 worktree，显示 branch/diff，支持 finish/cleanup。

这条路径能保持 CC Branch 的定位：它不是新的 Agent，也不是新的知识库，而是多 Agent CLI 的工作台和恢复层。

## 资料来源

本目录下每个项目文件都记录了源仓库、调研日期、commit 快照和主要阅读文件。调研基于 2026-06-11 至 2026-06-12 本地浅克隆的仓库内容，并用 GitHub 元数据做了二次校验。

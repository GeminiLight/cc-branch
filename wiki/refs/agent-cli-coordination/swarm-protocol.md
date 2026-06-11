<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: f0c9421c940aff15b41a9a0563aeb8299ebf3f44 -->

# swarm-protocol

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [phuryn/swarm-protocol](https://github.com/phuryn/swarm-protocol) |
| 语言 | TypeScript |
| License | MIT |
| 调研快照 | `f0c9421c940aff15b41a9a0563aeb8299ebf3f44`，2026-03-15 |
| 一句话定位 | 面向 Agent-first 团队的 MCP 状态同步协议。 |

## 解决的问题

`swarm-protocol` 假设场景是：多个开发者各自带着 Agent 在同一代码库里并行工作。它不试图提供 UI，也不接管终端，而是定义一个共享状态层，让 Agent 知道当前团队意图、任务领取、冲突和上下文。

## 架构方案

```text
Agent / MCP client
  -> MCP server
  -> PostgreSQL
  -> intents / claims / signals / context packages
```

技术栈是 Node.js、TypeScript、PostgreSQL 和 `@modelcontextprotocol/sdk`。v1 是 headless 协调层，没有 REST API 或 dashboard。

## 核心模型

- **Intent**：要完成的工作、背景、依赖和状态。
- **Claim**：某个 Agent/人认领某项工作。
- **Signal**：团队事件、状态变化、需要广播的信息。
- **Context Package**：Agent 开始工作前拉取的上下文包。

典型 Agent loop：

```text
get_team_status
  -> claim_work
  -> check_conflicts
  -> heartbeat
  -> complete_claim
```

## 协调机制

`get_context` 会组装 intent、父子依赖、active claims、recent signals、team conventions。它把“Agent 需要自己到处找上下文”变成一次 MCP 调用。

冲突检测偏 advisory，不做文件锁。身份也是 trust-based，`claimed_by` 是字符串，不是强认证主体。

## 对 CC Branch 的启发

- CC Branch 可以参考它的词汇：intent、claim、signal、context package。
- workspace 启动前的 `plan` 页面可以显示每个 Agent 的 intent 和工作目录。
- 如果未来做多人/远程协同，PostgreSQL/MCP 这种外部状态层可以作为可选 backend，而不是默认路径。

## 局限和风险

- PostgreSQL 对个人 CLI 工具来说偏重。
- 没有终端/session/worktree 恢复能力。
- 信任式 identity 适合团队内部实验，不适合安全边界明确的远程执行。

## 可参考实现点

- `get_context` 这种一次性上下文包值得借鉴：启动 Agent 前主动喂给它相关状态。
- `heartbeat` 可用于判断 Agent 是否卡住或失联。
- conflict advisory 可以与 CC Branch doctor 集成，作为启动/恢复前的提醒。

## 证据来源

- `README.md`
- `docs/SPEC.md`
- `src/db/schema.sql`

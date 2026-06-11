<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: 7ee4640f14153120c40c22164fa1f1e1237905e2 -->

# agent-kanban

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [saltbo/agent-kanban](https://github.com/saltbo/agent-kanban) |
| 语言 | TypeScript |
| License | FSL-1.1-ALv2 / Other |
| 调研快照 | `7ee4640f14153120c40c22164fa1f1e1237905e2`，2026-06-06 |
| 一句话定位 | 一个 Agent-first task board，用 daemon 和 worker agents 执行任务。 |

## 解决的问题

`agent-kanban` 偏团队任务流：人或 leader agent 创建任务，worker agent 认领、执行、开 PR，leader 审查和合并。它不是跨终端消息工具，而是 Agent workforce 的任务队列和控制台。

## 架构方案

```text
human / leader agent
  -> Hono API
  -> D1 / SQLite
  -> daemon polling
  -> worker agents in worktrees
  -> PR / review / merge
  -> board updates
```

Web UI 提供 board 和 chat，API 使用 Hono，daemon 在机器上轮询任务并启动 worker。GitHub 集成负责 PR 流程。

## 核心模型

- **Task lifecycle**：Todo -> In Progress -> In Review -> Done。
- **Agent identity**：leader/worker agent 有 Ed25519 keypair、fingerprint、JWT auth 和权限。
- **Delegation**：Agent 可以通过子任务委派。
- **Atomic claim**：通过 D1 batch 做任务领取。
- **Event bus**：当前有 daemon HTTP polling、Worker SSE、TunnelRelay WS，设计中迁移到 Durable Object WebSocket channel。

## 对 CC Branch 的启发

- Agent identity 和权限值得关注，尤其是远程 SSH 或共享机器场景。
- “worker 在 worktree 里执行”是一个成熟模式。
- 对状态变化用事件总线推给 UI，比 UI 轮询每个终端更干净。

## 不建议照搬的部分

它的 board、任务生命周期、PR review、身份授权都面向多人队列。CC Branch 的第一目标不是团队项目管理，所以不应该把这些流程作为主线。

## 可参考实现点

- Agent 身份和 fingerprint 可用于远程机器注册。
- stale detection 可用于识别卡住的 pane/session。
- Durable Object/WebSocket 事件总线的设计可以作为未来云同步参考。

## 证据来源

- `README.md`
- `DESIGN.md`
- `docs/designs/event-bus-migration.md`
- shared package snippets

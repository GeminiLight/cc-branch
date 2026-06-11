<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: 30b11f93847390b8f904a9205110c90d55f19529 -->

# ORCH

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [oxgeneral/ORCH](https://github.com/oxgeneral/ORCH) |
| 语言 | TypeScript |
| License | MIT |
| 调研快照 | `30b11f93847390b8f904a9205110c90d55f19529`，2026-05-19 |
| 一句话定位 | 一个终端里的多 Agent 编排器，管理任务、消息、共享上下文和生命周期。 |

## 解决的问题

ORCH 要解决的是“从一个 CLI/TUI 管一队 Agent”。它支持 Claude、Codex、Pi、Cursor 或任意 CLI，强调不需要数据库、云服务或 Docker。

## 架构方案

核心是 orchestrator tick loop：

```text
Reconcile
  -> Dispatch
  -> Collect
  -> update state
```

`Orchestrator` 会加载状态、处理 stale entries、调用 process manager、workspace manager、adapter、template engine、context store 和 message service。PID lock 防止多个 orchestrator 同时操作。

## 消息机制

`MessageService` 支持：

- direct message
- broadcast
- lead channel
- per-recipient fanout
- TTL
- pending mailbox

关键点是：消息不一定实时注入终端，而是在 `dispatchTask` 时被整理进 Agent prompt。这和 hcom 的 hook 注入不同，更像任务派发时的上下文打包。

## 记忆设计

仓库里有 Agent memory spec，方向包括：

- session memory：每个 agent-task 的 JSONL。
- activity log：append-only JSONL。
- agent knowledge store。
- 未来可能用 SQLite embeddings 做 semantic retrieval。

当前已有 ContextStore、retry context、task proof summary、feedback、workspace files 等实践。

## 对 CC Branch 的启发

- 对非实时消息，pending mailbox + prompt 注入比终端按键注入更稳。
- PID lock、stale entry 处理、state reconciliation 都适合 CC Branch 的运行态管理。
- `Reconcile -> Dispatch -> Collect` 可作为批量恢复/启动多个 Agent 的流程参考。

## 局限和风险

- ORCH 更偏任务编排，CC Branch 更偏项目工作台和环境恢复。
- 它强调 zero infra，但这也意味着跨进程实时可视化和持久查询能力会受限。
- Agent memory spec 部分仍是研究/规划性质，不能完全视为已实现能力。

## 可参考实现点

- pending mailbox drain into prompt。
- append-only activity log。
- PID lock 防重复 orchestrator。
- stale process cleanup。

## 证据来源

- `readme.md`
- `docs/AGENT_MEMORY_SPEC.md`
- `src/application/message-service.ts`
- `src/application/orchestrator.ts`

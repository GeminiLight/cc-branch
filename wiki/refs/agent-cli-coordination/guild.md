<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: 8766a5f280d18b043209d2962c7487965a7dc645 -->

# guild

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [mathomhaus/guild](https://github.com/mathomhaus/guild) |
| 语言 | Go |
| License | Apache-2.0 |
| 调研快照 | `8766a5f280d18b043209d2962c7487965a7dc645`，2026-05-26 |
| 一句话定位 | 一个本地 SQLite + MCP 的 Agent 任务、知识、规则和交接层。 |

## 解决的问题

Agent CLI 之间常见的协作问题是：一个 Agent 做到一半，另一个 Agent 不知道上下文；多个 Agent 同时认领同一件事；会话结束后经验丢在 transcript 里，下一次不能直接复用。

`guild` 把这些问题抽象成四个对象：

- **Quest**：正在做或待做的任务。
- **Lore**：长期知识。
- **Oath**：团队或项目规则。
- **Brief**：本次会话结束时留给下一个会话的交接摘要。

## 架构方案

`guild` 是一个单 Go 二进制，核心是本地 SQLite，主要入口是 MCP server。Claude Code、Codex、Cursor 等 MCP 客户端可以通过工具调用读取任务、写知识、领取工作和生成交接。

它的关键设计不是“控制终端”，而是“给多个 Agent 一个共享的工作记忆”：

```text
Agent CLI / IDE
  -> MCP tools
  -> guild binary
  -> embedded SQLite
  -> Quest / Lore / Oath / Brief
```

## 数据和检索

`guild` 使用本地 `~/.guild/` 状态目录。它的检索是 hybrid retrieval：BM25 关键词检索 + vector similarity，再用 reciprocal-rank fusion 合并排序。

这点和简单全文搜索不同：Agent 可以用自然语言找历史知识，也可以用精确关键字定位任务和规则。

## 协调机制

对多 Agent 来说，最有价值的是 Quest claim：

- Agent 可以原子领取 Quest，避免多人同时做同一任务。
- Quest 可以表达依赖关系，被上游阻塞时不会被错误推进。
- 完成 Quest 时可以写 brief，让后续会话接得上。
- Durable knowledge 写入 Lore，短期任务 scratchpad 写入 quest journal。

## 对 CC Branch 的启发

- CC Branch 可以不直接实现完整任务系统，但可以为 workspace 加一个“handoff brief”槽位。
- 如果未来做 Agent 协作，`claim` 比“谁先打开终端”更可靠。
- `doctor` 或 `plan` 可以读取共享规则/brief，启动时给 Agent 自动注入项目上下文。
- 记忆层适合通过 MCP 接入，不一定内置到 CC Branch。

## 局限和风险

- 它解决的是上下文和任务协调，不解决终端窗口恢复、pane layout、SSH opener 等运行环境问题。
- MCP 调用是显式工具调用，实时性不如 hook/event bus。
- 如果用户不维护 Quest/Lore/Brief，系统价值会下降。

## 可参考实现点

- `start session` 时一次加载 oath、latest brief、top quest。
- 原子 claim 可作为多 Agent 开工前的最小协作协议。
- Handoff brief 可以成为 CC Branch `stop` 或 `snapshot` 的可选动作。

## 证据来源

- `README.md`
- `docs/MODEL.md`
- `cmd/guild/mcp.go`
- `cmd/guild/init.go`

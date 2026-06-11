<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: ef5102c417cc36b74b464736acc4b919dbb1d2a4 -->

# wit

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [amaar-mc/wit](https://github.com/amaar-mc/wit) |
| 语言 | TypeScript |
| License | MIT |
| 调研快照 | `ef5102c417cc36b74b464736acc4b919dbb1d2a4`，2026-03-26 |
| 一句话定位 | 用 intent、symbol lock 和 contract 帮多个 Agent 在写代码前暴露冲突。 |

## 解决的问题

多个 Agent 同时改同一个代码库时，文件级冲突发现太晚。两个 Agent 可能改不同文件，却都在影响同一个函数、类型或 API contract。`wit` 关注的是“开工前协调”，不是“终端怎么打开”。

## 架构方案

`wit` 是一个轻量 daemon，使用 Bun、SQLite、Drizzle。Agent 通过 JSON-RPC 2.0 与 daemon 通信：

```text
Agent / Claude Code plugin
  -> JSON-RPC over Unix socket (.wit/daemon.sock)
  -> Hono/Bun daemon
  -> SQLite
  -> intents / locks / conflicts / contracts
```

HTTP POST `/rpc` 也可以作为调用入口。协议请求里包含 `witVersion`，便于演进。

## 核心模型

- **Intent**：Agent 声明自己准备做什么。
- **Lock**：对代码符号加锁，而不是只锁文件。
- **Conflict**：发现潜在冲突后给出 warning。
- **Contract**：对 API/函数签名等约束做声明，必要时通过 git pre-commit 阻止破坏性修改。

最关键的是 symbol lock。`wit` 用 Tree-sitter WASM 解析 TS/JS/Python，定位符号 byte range，锁的粒度可以是 `src/auth.ts:validateToken` 这样的符号路径。

## 冲突策略

`wit` 的冲突大多是 advisory warning，不是强制拦截。只有被接受的 contract signature change 才可能通过 pre-commit hook 阻止提交。

这是一种比较务实的设计：Agent 协作需要提醒，但不能频繁把自动化流程卡死。

## 对 CC Branch 的启发

- CC Branch 的 `doctor` 可以从路径检查升级到语义检查：同一项目多个 Agent 是否将编辑同一模块、同一符号或同一 API。
- 在 workspace plan 里可以展示 Agent intent，让用户启动前知道每个 pane/Agent 负责什么。
- SSH/local 混合场景下，intent/lock 比终端本身更能表达协作边界。

## 局限和风险

- daemon 生命周期、socket 路径和项目初始化会增加用户心智负担。
- 语义锁依赖 Tree-sitter 语言支持，不适合所有文件类型。
- warning 机制依赖 Agent 自觉遵守，不是强一致锁。

## 可参考实现点

- `.wit/daemon.sock` 这种项目级本地 socket 适合高频本机通信。
- `intents + locks + contracts` 可以作为 CC Branch 未来协作协议的词汇参考。
- pre-commit hook 适合拦截极少数明确高风险行为，不适合作为默认协作主路径。

## 证据来源

- `README.md`
- `docs/PROTOCOL.md`
- `src/daemon/server.ts`
- `src/db/schema.ts`

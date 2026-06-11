<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: 47d49f8d963c8b146b49973216f97a99750cdcd5 -->

# tutti

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [nutthouse/tutti](https://github.com/nutthouse/tutti) |
| 语言 | Rust |
| License | MIT |
| 调研快照 | `47d49f8d963c8b146b49973216f97a99750cdcd5`，2026-05-05 |
| 一句话定位 | 用 `tutti.toml` 把多 Agent 运维流程声明成代码。 |

## 解决的问题

`tutti` 的关键词是 Agent Ops。它不只是打开多个 Agent，而是希望像 Terraform 管基础设施一样管理 Agent 团队：角色、运行时、工作流、hook、gate、策略都写进配置。

## 架构方案

```text
tutti.toml
  -> roles / runtimes / workflows / hooks / gates / policies
  -> tmux sessions
  -> git worktrees
  -> dashboard / SSE
  -> run ledger / artifacts / review gates
```

runtime adapters 包括 Claude Code、Codex CLI、Aider、OpenClaw。每个 Agent 可以有自己的 tmux session 和 git worktree。

## 核心流程

Agent ops loop：

```text
Intake
  -> Execution
  -> Review
  -> Gate
  -> Record
```

它还关注 run ledger、artifact pipeline、budget guardrails、issue claim leases、cross-workspace registry 等运维能力。

## 终端控制

`tt send` 可以给 Agent 发 prompt，必要时自动启动 session，等待 idle/runtime signal，然后捕获 pane 输出。tmux adapter 会创建 detached session、导出环境变量、发送命令、capture pane，并用 tmux buffer/bracketed paste 发送多行内容。

## 对 CC Branch 的启发

- CC Branch 的配置也可以表达“角色 + opener + command + layout + policy”，但要比 `tutti.toml` 更轻。
- `tt send` 证明消息发送不一定要进 Agent 内部 API，终端层也可以完成很大一部分。
- run ledger 可以作为 CC Branch session history 的参考。

## 局限和风险

- Agent Ops 范围较大，容易把简单工作台变成流程引擎。
- tmux 是强依赖，对桌面端和 Windows 需要替代路径。
- gate/policy/budget guardrails 适合高级用户，不适合作为首屏复杂度。

## 可参考实现点

- `tutti.toml` 的声明式配置。
- tmux buffer/bracketed paste 发送多行 prompt。
- dashboard SSE 用于实时展示 terminal/run 状态。
- issue claim lease 可借鉴为 CC Branch 的“任务占用/Agent 忙碌状态”。

## 证据来源

- `README.md`
- `DESIGN.md`
- `src/cli/send.rs`
- `src/session/tmux.rs`
- `docs/AGENT_OPS_ROADMAP.md`

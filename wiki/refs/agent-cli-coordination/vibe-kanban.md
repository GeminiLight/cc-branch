<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: 4deb7eca8f381f7cbc1f9d15515a9ab8f8009053 -->

# vibe-kanban

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [BloopAI/vibe-kanban](https://github.com/BloopAI/vibe-kanban) |
| 语言 | Rust |
| License | Apache-2.0 |
| 调研快照 | `4deb7eca8f381f7cbc1f9d15515a9ab8f8009053`，2026-04-24 |
| 一句话定位 | 用看板、工作树、终端、预览和 diff 审查组织 coding agents。 |

## 解决的问题

当 Agent 不只是开几个终端，而是围绕 issue、分支、预览和 review 工作时，用户需要一个更完整的控制台。`vibe-kanban` 把任务、工作区、终端、开发服务器、代码 diff、评论和预览放到一个产品里。

## 架构方案

它是一个完整工作台，而不是单一协议：

```text
issue / task
  -> workspace
  -> git worktree attempt
  -> agent executor
  -> terminal logs / dev server / preview
  -> diff review / comments
```

Rust workspace 中能看到 executors、workspace-manager、worktree-manager、server、db、mcp、relay/remote/desktop bridge、preview proxy 等模块。

## 核心机制

- 每次 task attempt 对应一个 git worktree。
- Agent 在工作区里运行，有 branch、terminal、dev server。
- UI 支持 streaming logs、action approval、inline comments、diff review 和 app preview。
- 支持多种 coding agents，包括 Claude Code、Codex、Gemini CLI、GitHub Copilot、Amp、Cursor、OpenCode、Droid、CCR、Qwen 等。

## 对 CC Branch 的启发

- “工作区 = 分支 + 终端 + 预览 + diff” 是很好的用户心智模型。
- 如果 CC Branch 将来做桌面端，可以把 Agent session、terminal、diff、preview 做成一个项目内工作区，而不是单纯 pane 列表。
- 任务 attempt 和 worktree 绑定可以降低多 Agent 并行风险。

## 不建议照搬的部分

`vibe-kanban` 的产品边界比 CC Branch 大得多：它接近完整 coding agent workbench。CC Branch 当前更应该守住“多 Agent CLI 工作环境恢复和管理”，不要过早进入 issue/PR/preview 全流程。

## 可参考实现点

- worktree attempt 的生命周期。
- streaming logs 和 action approval 的 UI 模式。
- diff review 与 Agent 运行状态放在同一上下文里。
- executor 抽象，让不同 Agent CLI 被同一工作区模型管理。

## 证据来源

- `README.md`
- `docs/core-features/monitoring-task-execution.mdx`
- `docs/supported-coding-agents.mdx`
- workspace crate list

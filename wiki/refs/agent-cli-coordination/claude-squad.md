<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: 4a02a308be98053130223e7d80f7316a9264fb97 -->

# claude-squad

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [smtg-ai/claude-squad](https://github.com/smtg-ai/claude-squad) |
| 语言 | Go |
| License | AGPL-3.0 |
| 调研快照 | `4a02a308be98053130223e7d80f7316a9264fb97`，2026-05-18 |
| 一句话定位 | 用 TUI 管理多个 tmux-backed Agent 会话和 git worktree。 |

## 解决的问题

Agent CLI 多开后，用户需要在多个终端之间切换、查看 diff、恢复会话、处理分支。`claude-squad` 解决的是“多 Agent 终端工作台”，不是 Agent 之间的消息协议。

## 架构方案

```text
cs TUI
  -> tmux session per agent
  -> git worktree per instance
  -> session storage JSON
  -> diff / commit / push / resume operations
```

它支持 Claude Code、Codex、Gemini、Aider 等程序，通过 program/profile 配置启动不同 Agent。

## 核心机制

- **tmux 隔离**：每个 Agent 有自己的 tmux session，可以 attach、detach、capture。
- **worktree 隔离**：每个任务/实例有独立 git worktree 和 branch，降低并发冲突。
- **TUI 导航**：用户能在实例列表、终端、diff、提交操作之间切换。
- **状态序列化**：`InstanceData` 记录 title、path、branch、status、window size、program、worktree、diff stats 等。

## 对 CC Branch 的启发

- CC Branch 的 tmux-backed tab/pane 可以借鉴它的 session restore 和 worktree 绑定方式。
- 对用户来说，“看到每个 Agent 当前在哪个分支、改了多少文件、是否还在运行”比抽象任务名更有用。
- 终端恢复和 git worktree 应该在同一个 UI/配置模型里出现。

## 局限和风险

- 它不做跨 Agent messaging，也不做共享 memory。
- 强依赖 tmux，对 Windows 原生环境和非 tmux 用户需要替代方案。
- 它更像单机 TUI，不覆盖 SSH opener、桌面 UI、项目配置复用等 CC Branch 目标。

## 可参考实现点

- session storage 中记录 program、worktree、diff stats。
- TUI 中把 diff preview 和 terminal preview 放在同一工作流里。
- `resume`、`commit`、`push`、`checkout` 与 Agent session 绑定，减少用户在终端和 git 命令之间跳转。

## 证据来源

- `README.md`
- `session/tmux/tmux.go`
- `session/git/worktree.go`
- `session/storage.go`

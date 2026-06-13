<!-- Last verified: 2026-06-12 | Current stage: reference research | Source commit: 48108665e022fb87b5f498058af553694736af02 -->

# workmux

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [raine/workmux](https://github.com/raine/workmux) |
| 语言 | Rust |
| License | MIT |
| GitHub 元数据 | 1,614 stars；最近 push: 2026-06-06 |
| 一句话定位 | 把 git worktrees 和 tmux/zellij/kitty/WezTerm 窗口粘在一起的并行开发 workflow 工具。 |

## 解决的问题

`workmux` 不是完整 GUI，也不是 agent 协议层。它专注于一个高频工作流：为每个任务创建独立 worktree 和终端窗口，自动设置 pane、文件、hook，任务结束时合并并清理。

它很适合作为 CC Branch 的“worktree backend 参考”，因为它把 Git 生命周期、terminal multiplexer、Agent 启动、文件复制/软链、hook、merge cleanup 做成一条连续链路。

## 架构方案

```text
workmux add <branch/task>
  -> detect repo / config
  -> git worktree add
  -> copy/symlink files
  -> run post_create hook
  -> create multiplexer window/session
  -> run configured panes
  -> optional agent prompt injection

workmux merge/remove
  -> validate dirty state
  -> merge/rebase/squash into target
  -> run hooks
  -> remove worktree
  -> close mux window/session
  -> delete local branch
```

核心代码：

- `src/workflow/create.rs`：创建 worktree + multiplexer target。
- `src/git/worktree.rs`：`git worktree add/list/move/prune` 包装。
- `src/workflow/merge.rs`：merge/rebase/squash 和清理。
- `src/multiplexer/*`：tmux/zellij/kitty/WezTerm backend。
- `src/agent_setup/*`：Claude、Codex、Gemini、OpenCode、Pi 等 agent prompt/环境适配。

## Worktree 策略

workmux 的默认结构是 sibling worktree：

```text
~/projects/my-project/
~/projects/my-project__worktrees/feature-A/
~/projects/my-project__worktrees/bugfix-B/
```

关键能力：

- `worktree_dir` 可配置，支持 `~` 和 `{project}`。
- branch name 和 window name 可配置 prefix/naming。
- `files.copy` 和 `files.symlink` 处理 `.env`、`node_modules`、build cache。
- `post_create`、`pre_merge`、`pre_remove` 生命周期 hook。
- `panes`/`windows` 声明式配置，支持 `<agent>` 和 `<agent:codex>` placeholder。
- agent prompt injection 会根据 Claude、Gemini、Codex、OpenCode、Kiro、Vibe、Pi 自动选择参数格式。
- `workmux merge` 合并后可以删除 worktree、窗口、branch，也可 `merge_keep` 保留。

## 多 Terminal 处理

workmux 的特点是“尊重用户已有 terminal setup”。它抽象 multiplexer，但不替代它：

- tmux 是主路径。
- 也支持 zellij、kitty、WezTerm。
- 默认一个 worktree 对一个窗口或 session。
- pane layout 可以跑 agent、dev server、install、watcher。
- dashboard/sidebar 用于看 agent 状态、diff、发送命令。

这对 CC Branch 很关键：不要把“GUI pane”绑定死 tmux。可以抽象为 `layoutBackend`，让 direct、tmux、terminal emulator、SSH backend 共用同一 workspace model。

## 对 CC Branch 的启发

- **先把生命周期打通**：create/open/list/send/merge/remove/resurrect 比复杂看板更重要。
- **pane layout 和 worktree 创建应在同一次操作中完成**：用户创建 worktree 后马上要 agent/dev server/log pane。
- **文件同步是第一天需求**：`.env`、`.mcp.json`、`node_modules` 没处理好，worktree per agent 会很难用。
- **不要强制 tmux**：抽象 multiplexer/backend，给 tmux 用户高级体验，也给 GUI/direct 用户保留路径。
- **merge 前必须做安全检查**：目标 worktree 脏、源 worktree 未提交、同 branch 合并等都要阻断。

## 局限和风险

- 它是偏 CLI/tmux 用户的工具，GUI 信息架构不是重点。
- 它不管理 agent-native session id，也不是跨 Agent message bus。
- 对非 Git 项目或 Windows 原生 terminal 的适配不是核心主线。

## 可参考实现点

- `workmux add` 的 create preflight 和 target collision 处理。
- `workmux merge` 的 target branch 检测、dirty state 检查和 cleanup。
- `files.copy`/`files.symlink` 配置模型。
- `panes`/`layouts`/`agent placeholder` 的声明式写法。
- multiplexer backend trait。

## 证据来源

- `README.md`
- `src/workflow/create.rs`
- `src/git/worktree.rs`
- `src/workflow/merge.rs`
- `src/multiplexer/tmux.rs`
- `src/agent_setup/codex.rs`
- `src/agent_setup/claude.rs`

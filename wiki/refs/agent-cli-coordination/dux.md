<!-- Last verified: 2026-06-12 | Current stage: reference research | Source commit: 1481b83829d7e237c7ad87097406fb72ae1fca16 -->

# dux

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [patrickdappollonio/dux](https://github.com/patrickdappollonio/dux) |
| 语言 | Rust |
| License | MIT |
| GitHub 元数据 | 53 stars；最近 push: 2026-06-11 |
| 一句话定位 | 轻量终端 TUI：多个 AI coding agents 并排运行，每个 agent 一个 git worktree，并配 companion terminals、macros、commit/diff/PR 功能。 |

## 解决的问题

`dux` 的产品判断很直接：不要协议层，不要 adapter，不要 JSON-RPC，让真实 CLI 运行在真实 PTY 里。它把项目、agent、worktree session 组织到一个 TUI 中，让用户同时看多个 agent、多个 diff 和 companion terminals。

与 CC Branch 相比，它更像轻量单机 TUI；但它对“任何 CLI 都能接入”的思路很适合 CC Branch。

## 架构方案

```text
dux TUI
  -> projects
  -> agent sessions
  -> git worktree per agent
  -> PTY provider command
  -> companion terminals
  -> git pane: stage/diff/commit/push/PR status
  -> SQLite session store
```

关键文件：

- `src/model.rs`：Project、AgentSession、branch/worktree/session 字段。
- `src/startup.rs`：startup command 在 worktree 中执行，并注入 env。
- `src/cli.rs`：config reset、worktree 清理、session DB 管理。
- `src/session_store.rs` 或相关 store 模块：session 持久化。

## Worktree 策略

- 创建 agent 时从项目创建新 branch + worktree。
- 一个 agent 对应一个 worktree。
- 可从已有 worktree 创建 agent；如果外部 worktree 不在 dux 管理目录下，会复制进新的 managed worktree，避免污染原 checkout。
- Provider 可以在同一个 worktree 上切换，下次启动时使用新 provider；支持 resume args 则恢复原对话。
- Fork session 会创建新 worktree，并复制当前文件状态，让用户尝试另一条路线。
- `config reset` 默认保留 agents/worktrees，`reset --all` 才删除 session 和 worktree，避免误删。

## 启动环境

dux 支持 project startup command：

- 在新 agent worktree 中运行。
- 失败不会阻止 agent 创建，只在状态行展示并可查看 log。
- 注入 `DUX_PROJECT_PATH`、`DUX_WORKTREE_PATH`、`DUX_AGENT_ID`、`DUX_AGENT_BRANCH`、`DUX_PROVIDER`、`DUX_STARTUP_COMMAND_LOG`。
- provider 是 config-only：默认 Claude、Codex、Gemini、OpenCode，也可自定义命令和 resume args。

这对于 CC Branch 的 template/profile 有参考价值：profile 不只写 agent 命令，也要能写 setup command、环境变量、resume 参数。

## 对 CC Branch 的启发

- **任何 CLI 都应是 provider**：不要把 Claude/Codex 写死；profile 配置 command/args/resume_args。
- **companion terminal 是刚需**：agent 旁边需要 build/test/git shell，不应该只给一个 agent pane。
- **reset/cleanup 要分级**：普通 reset 不删工作成果，强操作才删 worktree。
- **startup command 失败不应阻断**：创建工作区成功比 setup 全绿更重要，失败作为状态暴露给用户。
- **fork 是 worktree + 文件状态 + provider session 的组合**。

## 局限和风险

- star 还低，项目很新，需要观察稳定性。
- 不做 tmux 持久 session；它更依赖自己的 PTY/TUI runtime。
- 没有完整跨 Agent messaging 或共享 memory。

## 可参考实现点

- provider config 的 `command`/`args`/`resume_args`。
- project startup command 和环境变量。
- agent/worktree/session SQLite store。
- existing worktree import/copy 策略。
- companion terminals 与 agent worktree 共目录。

## 证据来源

- `README.md`
- `src/model.rs`
- `src/startup.rs`
- `src/cli.rs`

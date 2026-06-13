<!-- Last verified: 2026-06-12 | Current stage: reference research | Source commit: 6f036b389eae7f83fd6634e04edf3ffe3f4cbbdc -->

# Agent of Empires

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [agent-of-empires/agent-of-empires](https://github.com/agent-of-empires/agent-of-empires) |
| 语言 | Rust |
| License | MIT |
| GitHub 元数据 | 2,559 stars；最近 push: 2026-06-11 |
| 一句话定位 | 用 TUI 和 Web dashboard 管理多个 tmux-backed AI agent session，每个 session 可绑定 git worktree 和 Docker sandbox。 |

## 解决的问题

`Agent of Empires` 解决的是“多 Agent 已经跑起来之后，用户怎么持续看、接、停、恢复、远程访问”的问题。它比纯 tmux 多了 agent-aware 状态、worktree 创建/清理、diff、Web/PWA 访问、ACP 结构化视图和 Docker sandbox。

它的产品形态和 CC Branch 很接近：不是新的 coding agent，而是把 Claude Code、Codex CLI、Gemini CLI、OpenCode、Pi、Copilot CLI 等真实 CLI 托管在可恢复的 session 里。

## 架构方案

```text
aoe TUI / CLI / HTTP API
  -> session registry / profile config
  -> tmux session per agent
  -> optional git worktree per session
  -> optional Docker sandbox
  -> status detector / session id capture
  -> Web dashboard / ACP structured view / diff viewer
```

核心代码分布：

- `src/tmux/session.rs`、`src/tmux/status_detection.rs`：tmux session 创建、状态检测。
- `src/git/worktree.rs`、`src/git/diff.rs`：worktree 和 diff。
- `src/session/builder.rs`、`src/session/storage.rs`：session 创建与持久化。
- `src/session/capture.rs`：Claude/Pi/Vibe/OpenCode 等 CLI 的 session id 捕获。
- `src/server/api/*`、`src/server/ws.rs`、`src/server/acp_ws.rs`：Web/API/WS 控制面。

## Worktree 策略

- 创建 session 时可以自动创建 branch + git worktree。
- 删除 session 时可以联动清理 worktree。
- 支持 multi-repo workspace：一个 session 可以同时挂多个 repo，适合跨服务任务。
- diff 视图直接使用 session 的 worktree 状态，Web 和 TUI 都能看。

对 CC Branch 的启发是：worktree 不应该只是一个 Git 操作按钮，而应该成为 session 的一等字段。UI 上至少要能看到 `session -> repo/worktree -> branch -> diff -> status`。

## 终端与恢复

每个 agent 跑在独立 tmux session 中。TUI 关闭、SSH 断开、终端崩溃后，tmux session 继续存在；再次打开 `aoe` 时从 session storage 和 tmux 状态恢复。

它还对各 CLI 做 session id capture：

- Claude Code：扫描 `~/.claude/projects/{encoded-path}/` 的 jsonl，并优先读取 hook 写出的 session id。
- Pi/Vibe/OpenCode：读取各自 session 文件或 SQLite store。
- Docker 内运行时，通过 `docker exec` 在容器内扫描 session 文件。
- 为避免多个 AoE session 抢同一个 CLI session id，会通过 tmux hidden env 建 exclusion set。

这点直接回答了“hook 能不能把重新开始的 session 拿回来”：可以，但要把 hook 信号和文件扫描结合起来。hook 是快路径，文件扫描是兜底，tmux env/session registry 是去重锚点。

## 状态与 Web UI

AoE 把状态做成产品主线：

- `Running` / `Waiting` / `Idle` / `Error` 状态来自 tmux pane 内容和 agent-specific heuristic。
- Web dashboard 可以渲染真实 terminal，也可以用 Agent Client Protocol 做结构化 view。
- 支持 diff viewer、tool cards、approval flows、token auth、远程 QR/passphrase pairing。

这说明“Workspace 页面”不一定只显示 layout；它应该逐步变成 session command center。

## 对 CC Branch 的启发

- **把 pane、agent session、worktree 绑定成一个实体**：不要让 UI 只知道 pane 位置，而不知道这个 pane 属于哪个 branch 和 CLI session。
- **hook + scan 双路径恢复**：hook 写 session id；后台扫描 transcript/session 文件兜底；用 registry 排除被其他 pane/session 占用的 id。
- **Web dashboard 不等于 terminal iframe**：结构化状态、diff、approval、mobile view 会比裸终端更有价值。
- **API 要能驱动 session**：CLI、GUI 和未来其他 agent 都应该调用同一组 session API，而不是各写一套。

## 局限和风险

- tmux 是强依赖，Windows 原生场景需要替代 backend。
- 功能面很广，容易把 CC Branch 带向完整 agent workstation，而不是轻量 workspace orchestrator。
- ACP 结构化视图依赖 agent/provider 支持；对普通 shell 或不支持协议的 CLI 仍要保留 terminal fallback。

## 可参考实现点

- session id capture 的 hook + file scan + tmux env 去重模型。
- TUI/Web/API 共享 session registry。
- worktree 与 session 删除/恢复生命周期绑定。
- Web dashboard 中 raw terminal 与 structured view 双模式。
- multi-repo session 对跨仓库任务的表达方式。

## 证据来源

- `README.md`
- `docs/features.md`
- `docs/guides/worktrees.md`
- `src/session/capture.rs`
- `src/tmux/status_detection.rs`
- `src/git/worktree.rs`
- `src/server/api/sessions.rs`

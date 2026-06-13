<!-- Last verified: 2026-06-12 | Current stage: reference research | Source commit: fa2598155e449a0f6538a0fe2b2caeddb940920a -->

# TermCanvas

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [blueberrycongee/termcanvas](https://github.com/blueberrycongee/termcanvas) |
| 语言 | TypeScript / Electron |
| License | MIT |
| GitHub 元数据 | 321 stars；最近 push: 2026-05-31 |
| 一句话定位 | 用无限画布管理 terminal，按 Project -> Worktree -> Terminal 组织 Claude/Codex/shell/tmux/lazygit，并通过 hooks/telemetry 追踪 session 状态。 |

## 解决的问题

`TermCanvas` 从空间画布角度解决“开了太多 terminal/pane”的问题。它不是传统 tab/split UI，而是让用户把终端铺在无限 canvas 上，按项目、worktree、terminal 三层组织。

这和 CC Branch 的 Workspace GUI 很相关：如果 CC Branch 要支持 pane 拖拽、自由布局、跨 worktree terminal，可借鉴它的层级模型和 telemetry。

## 架构方案

```text
Electron app
  -> project scanner
  -> worktree scanner / git watcher
  -> terminal runtime / PTY manager
  -> canvas layout store
  -> Claude/Codex hooks + session watcher
  -> telemetry truth layer
  -> Hydra CLI orchestration
```

关键文件：

- `electron/project-scanner.ts`、`electron/git-watcher.ts`、`electron/git-info.ts`：项目和 worktree/git 状态。
- `electron/pty-manager.ts`、`electron/terminal-state.ts`：终端生命周期。
- `electron/hook-receiver.ts`、`shared/telemetry.ts`：hook/telemetry。
- `src/stores/*`、`src/migration/migrateToFreeCanvas.ts`：canvas 状态和布局。
- `README.md` 中的 `termcanvas` / `hydra` CLI 文档。

## Worktree 与 Terminal 策略

- 层级固定为 Project -> Worktree -> Terminal。
- 添加项目时自动发现 worktree。
- 用户从 terminal 创建新 worktree 后，canvas 自动出现。
- 每个 worktree 可以有 Claude、Codex、shell、tmux、lazygit 等 terminal。
- Sessions Panel 按 projects -> worktrees -> sessions 组织历史 Claude/Codex 对话。
- Git status/diff/commit history 在侧栏可见。

## Hydra Orchestration

TermCanvas 内置 `hydra`：

- 协调 git worktrees、assignment/run 文件契约、telemetry。
- Lead terminal 决定任务拆分；worker terminals 自主执行。
- Workbench state 在 `.hydra/workbenches/`。
- 权威交付物是 `intent.md`、`report.md`、`result.json`、`ledger.jsonl`，terminal 文本只作为参考。
- 角色注册目前面向 Claude/Codex。

这和 CC Branch 的长期方向有关：如果未来做多 Agent 协作，不一定先做聊天总线；也可以先用 repo-local 文件契约和 telemetry 做轻量协调。

## 对 CC Branch 的启发

- **Workspace GUI 应该有 worktree 层级**：pane/terminal 不应只悬浮在 tab 中，要能归属到 project/worktree。
- **自由 canvas 能解决多终端拥挤**：drag、zoom、focus chain、box select 比固定 grid 更适合长期多 Agent。
- **hook/telemetry 是状态可信源**：terminal 输出只能作为展示，状态判断需要 hook、session file、process、git watcher 多信号融合。
- **CLI 控制面要机器可读**：`termcanvas state dump --json`、`terminal status`、`diff --summary` 这类接口适合被 agent 调用。
- **文件契约比聊天更稳**：`result.json`、`ledger.jsonl` 可作为完成/失败判据。

## 局限和风险

- 产品边界很大，包含画布、记忆、Hydra、云路线，不能整体照搬。
- Electron 架构与 CC Branch 的 Python backend/Tauri desktop 不同。
- Infinite canvas 的交互复杂度高，需要很强 QA，否则会比 tab/pane 更难用。

## 可参考实现点

- Project -> Worktree -> Terminal 数据模型。
- worktree scanner 和 terminal scanner 联动。
- Claude/Codex hook trust 与 telemetry fallback。
- canvas layout 持久化。
- repo-local `.hydra/workbenches/` 文件契约。

## 证据来源

- `README.md`
- `shared/telemetry.ts`
- `shared/lifecycleThresholds.ts`
- `electron/project-scanner.ts`
- `electron/git-watcher.ts`
- `electron/hook-receiver.ts`
- `src/migration/migrateToFreeCanvas.ts`

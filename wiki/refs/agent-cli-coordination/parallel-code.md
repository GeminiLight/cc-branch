<!-- Last verified: 2026-06-12 | Current stage: reference research | Source commit: d5338956bc067641cb769bded51a22b54c5fa23f -->

# Parallel Code

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [johannesjo/parallel-code](https://github.com/johannesjo/parallel-code) |
| 语言 | TypeScript / Electron / SolidJS |
| License | MIT |
| GitHub 元数据 | 715 stars；最近 push: 2026-06-10 |
| 一句话定位 | Electron 桌面工作台：为每个任务创建 git branch + worktree，运行 Claude/Codex/Gemini/Copilot，并在 GUI 中 review diff、merge 或丢弃。 |

## 解决的问题

`Parallel Code` 不是终端复用工具，而是桌面 agent task workbench。它把用户心智设成：

```text
task = branch + worktree + agent process + terminals + diff/review state
```

这与 CC Branch 的 GUI 方向高度相关：工作区界面不能只是静态 pane canvas，还要能表达“每个 pane/task 正在改哪条 branch、哪些文件、是否能合并”。

## 架构方案

```text
Electron main process
  -> IPC create_task / merge_task / git APIs
  -> git worktree manager
  -> PTY agent process
  -> optional Docker isolation
  -> renderer store: project/task/agent/terminal state
  -> diff review / steps tracking / mobile remote
```

关键文件：

- `electron/ipc/git.ts`：Git 和 worktree 操作。
- `electron/ipc/tasks.ts`：create task 调用 worktree 创建。
- `src/store/tasks.ts`：任务、agent、worktree、MCP/coordinator 状态写入 store。
- `electron/ipc/pty.ts`：PTY agent 运行。
- `electron/mcp/coordinator.ts`：coordinator/sub-task MCP。

## Worktree 策略

创建任务时：

1. 从 base branch 创建新 branch。
2. 创建 git worktree。
3. symlink `node_modules`、`.env` 等 gitignored 目录或文件。
4. spawn AI agent 到 worktree。
5. 在 renderer store 中保存 `taskId`、`branchName`、`worktreePath`、`agentIds`。

实现细节值得注意：

- `withWorktreeLock` 用 repo/worktree key 串行化 worktree 操作，避免同时创建/移除造成 Git state 竞争。
- `.claude/` 不简单 symlink，而是复制必要文件，避免 Claude Code bwrap sandbox 对 symlink bind mount 失败。
- `.git/info/exclude` 会写入 symlink exclude，避免 symlink 被 git status 污染。
- 支持 direct mode：也可以在当前 branch 直接跑，但同项目只允许一个 direct task，降低互踩风险。
- 支持 import existing worktree，把外部已有 worktree 纳入 task 模型。

## 多 Agent 与 Coordinator

Parallel Code 有 coordinator mode：

- 启动 coordinator 任务前，先启动 MCP server。
- Coordinator 可以派发 sub-task，sub-agent 在自己的 worktree 中执行。
- task store 记录 coordinator/children 关系、MCP config、launch args、最大并发数。
- 每个 task 可以维护 `.claude/steps.json`，作为工程经理视图。

这说明“多 Agent 并行”可以先用 worktree/task 隔离，再用 MCP/coordinator 做上层调度；不要一开始就把所有 agent 放到一个共享 terminal 里。

## 对 CC Branch 的启发

- **GUI 中 task/worktree 是一等实体**：pane 拖拽只是 layout；真正高价值是把 pane 绑定到 branch、diff、agent status。
- **worktree 操作要加锁**：同一 repo 下并发 `git worktree add/remove` 必须串行化。
- **Claude/Codex 的运行环境有特殊坑**：`.claude/`、sandbox、gitignored 文件不能只靠简单 symlink。
- **支持导入既有 worktree**：用户可能已经手动建了 worktree，CC Branch 应该能 adopt，而不要求重新创建。
- **coordinator 可以后置**：先做好 task/worktree/agent，再接 MCP coordinator。

## 局限和风险

- 它偏完整桌面应用，产品范围比 CC Branch 当前 CLI 初始化/工作区恢复更重。
- Electron PTY 和本项目 Python/Web/Tauri 架构不同，只能参考模型，不能直接搬代码。
- Worktree 自动创建会改变用户 Git 习惯，必须可选且可解释。

## 可参考实现点

- `GitIsolationMode = worktree/direct/none` 的选项模型。
- worktree lock。
- `.claude/` 复制与 symlink exclude。
- import existing worktree。
- task store 中 `branchName`、`worktreePath`、`agentIds` 的绑定方式。
- coordinator MCP 启动时机。

## 证据来源

- `README.md`
- `electron/ipc/git.ts`
- `electron/ipc/tasks.ts`
- `src/store/tasks.ts`
- `electron/mcp/coordinator.ts`

<!-- Last verified: 2026-06-12 | Current stage: reference research | Source commit: 47f41188bf37c8f37c5947d39c2b939d63f4bb2e -->

# Agent Deck

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [asheshgoplani/agent-deck](https://github.com/asheshgoplani/agent-deck) |
| 语言 | Go |
| License | MIT |
| GitHub 元数据 | 2,685 stars；最近 push: 2026-06-11 |
| 一句话定位 | 面向 Claude、Codex、Gemini、OpenCode 等 CLI 的终端 session manager，带 worktree、fork、conductor、watcher、inbox 和 Docker sandbox。 |

## 解决的问题

`Agent Deck` 关注“已经有很多 AI coding agent session，如何统一看、分组、搜索、fork、恢复、远程通知”。它的定位是 mission control，不是项目管理看板。

它和 CC Branch 的交集很大：多 session、tmux、CLI provider、worktree、hook、session fork、inbox、Web UI、Docker sandbox。

## 架构方案

```text
agent-deck TUI / CLI / Web
  -> session registry
  -> tmux pane/session control
  -> provider adapters: Claude / Codex / Gemini / OpenCode / custom
  -> worktree manager
  -> hook handlers / inbox / watcher
  -> optional Docker sandbox
```

关键文件：

- `cmd/agent-deck/session_cmd.go`：session 管理入口。
- `cmd/agent-deck/worktree_cmd.go`：worktree list/info/finish/cleanup。
- `cmd/agent-deck/session_send_keys_cmd.go`：向 session 发送输入。
- `cmd/agent-deck/hook_handler.go`：agent hook 接入。
- `cmd/agent-deck/conductor_cmd.go`：conductor session。

## Worktree 策略

Agent Deck 的 worktree 设计非常细：

- `agent-deck add . -c claude --worktree feature/a --new-branch` 创建新 worktree session。
- `agent-deck worktree finish <session>` 合并分支、删除 worktree、删除 session。
- `agent-deck worktree cleanup` 找 orphaned worktree/session。
- worktree 默认位置可配：sibling、repo 内 `.worktrees/`、自定义根目录。
- `.worktreeinclude` 按 gitignore-syntax 复制 `.env`、`.mcp.json`、secrets 等 gitignored 文件。
- `.agent-deck/worktree-setup.sh` 在创建 worktree 后运行，拿到 `AGENT_DECK_REPO_ROOT` 和 `AGENT_DECK_WORKTREE_PATH`。
- 支持 bare repo 布局，包括 nested `.bare/` 和 true-bare-at-root。

这给 CC Branch 一个明确结论：如果做 Worktree per Agent，必须同时设计 gitignored 文件复制、setup hook、路径约定、bare repo、cleanup，否则用户会很快遇到“worktree 是空的/跑不起来/不好收尾”。

## Forking 与 Session 继承

Agent Deck 支持 Claude、OpenCode、Pi、Codex 的 native fork。快速 fork 默认会：

- 创建新 branch + worktree。
- 携带父 session 的未提交改动和 gitignored 文件。
- 继承 Docker isolation。
- 继承 Claude launch options。

这比简单 `git worktree add` 更贴近 agent 工作流：用户要 fork 的通常是“代码状态 + 对话上下文 + 运行环境”。

## 对 CC Branch 的启发

- **Worktree setup 是产品功能，不是脚本细节**：`.worktreeinclude` 和 setup script 很值得吸收。
- **finish/cleanup 必须一等支持**：只创建 worktree 不够，合并、删除、孤儿清理才决定用户能否长期用。
- **fork session 要合并对话和 Git 语义**：对于 Codex/Claude 这种有 session id 的 CLI，fork 应尝试调用 provider-native fork。
- **per-group config 有价值**：不同团队/账号/agent profile 可以用不同 config dir/env。
- **inbox/hook 可以逐步接入**：先把消息送到终端，再逐步升级为 agent-native hook。

## 局限和风险

- 功能范围已经接近完整 agent control plane，复杂度明显高于 CC Branch 当前定位。
- 大量能力围绕 tmux 实现，对 Windows 原生和 GUI direct backend 需要抽象层。
- 如果 CC Branch 照搬 conductor/watchers，容易过早进入“agent 团队管理”，而不是先做好 workspace restore。

## 可参考实现点

- `worktree finish` 的 merge + session delete + worktree remove。
- `.worktreeinclude` 文件复制语义。
- `.agent-deck/worktree-setup.sh` 生命周期 hook。
- bare repo/worktree path 解析。
- session fork 默认继承 code state、CLI state、Docker state。

## 证据来源

- `README.md`
- `cmd/agent-deck/worktree_cmd.go`
- `cmd/agent-deck/session_cmd.go`
- `cmd/agent-deck/session_send_keys_cmd.go`
- `cmd/agent-deck/hook_handler.go`

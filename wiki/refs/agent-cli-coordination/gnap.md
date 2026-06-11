<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: 2571f5574a0e28001638030222ad7f8bb65b57f7 -->

# GNAP

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [farol-team/gnap](https://github.com/farol-team/gnap) |
| 语言 | 协议/文档为主 |
| License | MIT |
| 调研快照 | `2571f5574a0e28001638030222ad7f8bb65b57f7`，2026-03-17 |
| 一句话定位 | 用 git 和 `.gnap/` JSON 文件做零服务端 Agent 协议。 |

## 解决的问题

很多 Agent 协作方案需要 daemon、数据库、MCP server 或云服务。GNAP 走了另一条路：既然开发者已经有 git，就把 Agent 协作状态也放进仓库，用 commit history 做审计。

## 架构方案

仓库内有一个 `.gnap/` 目录：

```text
.gnap/
  version
  agents.json
  tasks/*.json
  runs/*.json
  messages/*.json
```

Agent 的工作循环很简单：

```text
git pull
  -> read agents/tasks/messages
  -> do work
  -> write run/message/task update
  -> git commit
  -> git push
  -> sleep
```

## 核心模型

- **Agent**：声明身份、能力、状态。
- **Task**：待处理或进行中的任务。
- **Run**：某次 Agent 执行记录，可包含 token/cost 等统计。
- **Message**：Agent 或人之间的消息。

这套模型不追求实时，而是追求可移植、可审计、零依赖。

## 对 CC Branch 的启发

- CC Branch 的项目配置本来就适合提交到仓库；GNAP 证明“配置即协议”对 Agent 协作很自然。
- 可以考虑把某些可共享状态放进项目目录，把运行态和敏感状态留在 `~/.cc-branch/`。
- 对远程 SSH 场景，git-native 同步可以作为低实时性、强审计的备选方案。

## 局限和风险

- 实时性弱，不能很好支持“立刻给另一个终端里的 Agent 插消息”。
- git 冲突处理需要 discipline，Agent 写 JSON 时要避免格式冲突。
- 不适合高频事件流，例如终端输出、按键注入、实时状态。

## 可参考实现点

- `.gnap/` 的 schema 化目录结构。
- run 文件记录 token/cost/结果，适合 CC Branch 未来做 session snapshot。
- git history 作为 Agent 协作审计日志，可以补充本地 SQLite 日志。

## 证据来源

- `README.md`
- `docs/article.md`
- `examples/.gnap/agents.json`
- `examples/.gnap/tasks/*.json`
- `examples/.gnap/runs/*.json`
- `examples/.gnap/messages/*.json`

<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: bda8a13cd58003c5607fd38863f2962aa8d98e41 -->

# shire

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [victor36max/shire](https://github.com/victor36max/shire) |
| 语言 | TypeScript |
| License | MIT |
| 调研快照 | `bda8a13cd58003c5607fd38863f2962aa8d98e41`，2026-05-03 |
| 一句话定位 | 一个让多个持久 Agent 通过 outbox、shared drive 和 Web UI 协作的宿主环境。 |

## 解决的问题

`shire` 不是跨终端工具。它更像一个本地 Agent 后台：用户创建多个 Agent，每个 Agent 有自己的 harness、模型、系统提示、技能和目录；Agent 可以给彼此发消息，也可以在共享目录里协作。

## 架构方案

技术栈：

- Runtime：Bun
- Backend：Hono、Drizzle ORM、SQLite
- Frontend：React 19、React Router、shadcn/ui、Tailwind
- Agent harness：Claude Code SDK、OpenCode SDK、Pi Agent SDK、Codex SDK

运行结构：

```text
Web UI / API
  -> ProjectManager
  -> Coordinator per project
  -> AgentManager per agent
  -> Harness SDK
  -> SQLite messages + filesystem workspace
```

## 文件工作区

数据默认在 `~/.shire/`。每个 project 有自己的目录：

```text
project/
  PROJECT.md
  peers.yaml
  shared/
  agents/<agent-id>/
    inbox/
    outbox/
    attachments/
    .claude/ or .agents/
```

Agent 的内部 prompt 会告诉它：读 `peers.yaml` 找同伴，写 YAML 到 `outbox/` 给其他 Agent 发消息，写 `shared/` 做共享产物。

## 消息机制

`shire` 的消息不是靠终端注入，而是应用层路由：

1. Agent 写 `outbox/<name>.yaml`。
2. `AgentManager` 监听 outbox。
3. `Coordinator` 收到 `project:{id}:outbox` event。
4. 如果目标是普通 Agent，就路由到目标 Agent；如果是 `system_alert`，就发通知。
5. 消息写入 SQLite `messages` 表，并通过 WebSocket event 推给 UI。

WebSocket 订阅使用 topic，例如 `project:{id}:agent:{aid}`、`project:{id}:agents`、`shared-drive:{projectId}:{path}`。

## Shared Drive

`shared/` 是项目级共享目录。后端有 shared drive API 和 watcher，订阅 shared-drive topic 后会用 `fs.watch` 监听文件变化，debounce 后通过 EventBus 发 `file_changed`。

这是一种很直观的协作方式：把“共享记忆”降低成“共享文件夹 + 搜索 + 预览 + 编辑”。

## 对 CC Branch 的启发

- outbox/inbox 文件通信适合跨 Agent，也适合 SSH 场景，因为文件比进程 API 更容易同步。
- 每个 Agent 有独立目录，shared drive 单独隔离，这是清楚的文件边界。
- WebSocket topic 模型可以用于 CC Branch 桌面端显示 Agent 状态和文件变化。
- `peers.yaml` 可以对应 CC Branch 的 project agent registry。

## 局限和风险

- 它依赖 SDK/harness，不是“原样保留用户终端里的 CLI”。
- Agent 在宿主环境内运行，迁移现有终端工作流成本更高。
- outbox YAML 机制简单，但如果高频消息或复杂附件增多，需要更多队列和重试语义。

## 可参考实现点

- `agents`、`messages`、`scheduled_tasks`、`alert_channels` 这些表的边界比较清楚。
- `buildInternalPrompt` 把通信协议直接写进 Agent prompt，降低工具调用依赖。
- shared drive watcher 的 refcount 和 debounce 处理适合桌面 UI。

## 证据来源

- `README.md`
- `src/db/schema.ts`
- `src/events.ts`
- `src/runtime/coordinator.ts`
- `src/runtime/agent-manager.ts`
- `src/runtime/system-prompt.ts`
- `src/services/shared-drive-watcher.ts`
- `src/routes/messages.ts`

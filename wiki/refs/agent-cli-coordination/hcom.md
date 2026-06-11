<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: c5032a41342205971eb014da2bbf3e55501eed50 -->

# hcom

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [aannoo/hcom](https://github.com/aannoo/hcom) |
| 语言 | Rust |
| License | MIT |
| 调研快照 | `c5032a41342205971eb014da2bbf3e55501eed50`，2026-06-10 |
| 一句话定位 | 给 Claude Code、Codex、Gemini、Cursor CLI 等 Agent CLI 加一个跨终端消息和观察层。 |

## 解决的问题

多个 Agent CLI 分散在不同终端里时，最大的问题不是“能不能多开”，而是它们彼此不可见：不知道谁在运行、谁改了文件、谁需要帮助，也不能在对方正在工作时插入一条消息。

`hcom` 的做法是把 Agent 启动包一层，例如 `hcom claude`、`hcom codex`。被包住的 Agent 仍然在原来的终端和 CLI 里运行，但 hcom 通过 hook、SQLite 和终端观察把它们连成一个本地消息网络。

## 架构方案

核心路径可以概括为：

```text
agent process
  -> hooks / terminal observer
  -> local SQLite
  -> delivery hook / wakeup
  -> target agent
```

主要模块：

- **包装启动器**：用户用 `hcom <agent-cli>` 启动 Agent，hcom 负责注入环境变量、hook 和 session 绑定。
- **本地 SQLite**：记录 instances、events、messages、notify endpoints、process/session bindings 等状态。
- **hook 投递**：Agent 活动被 hook 写入数据库；目标 Agent 的消息通过 hook 注入，空闲 Agent 可以被唤醒。
- **观察能力**：可读取 Agent 的 transcript、terminal screen、command history、file edit event。
- **冲突提醒**：默认检测 30 秒内多个 Agent 编辑同一文件的情况，并通知相关 Agent。
- **跨设备 relay**：可选 MQTT relay，使用 XChaCha20-Poly1305 加密和预共享密钥。

## 通信模型

`hcom` 不是让 Agent 直接互相开 socket，而是把消息落到本地数据库，再由 hook 触发投递。这样做的好处是：

- 消息有持久记录，终端关闭或 Agent 暂停后仍能查询。
- Agent 不需要知道对方的进程地址，只需要知道对方的 hcom identity。
- 可以在消息之外记录事件，例如文件编辑、命令历史、屏幕状态。
- UI/CLI 可以从同一个数据库读状态。

它更像一个本机 Agent event bus，而不是任务管理器。

## 跨设备能力

`hcom` 的 relay 方案是 MQTT broker + 端到端加密。token 中包含 relay id、broker URL 和原始 PSK。安全边界比较清楚：一旦 token 泄漏，风险接近“把远程 shell 能力交出去”，因为接收端 Agent 可能会执行收到的指令。

这说明跨设备 Agent 通信要谨慎放进主路径。对 CC Branch 来说，本机/SSH 的显式连接应该优先于默认云 relay。

## 对 CC Branch 的启发

- 可以为每个 pane/session 建一个稳定 Agent identity，而不是只记录 tmux session 名。
- 可以把消息、终端快照、最近输出和文件编辑事件放进一个轻量 event log。
- `doctor` 可以增加“多 Agent 同文件编辑风险”检查。
- 不必强制所有 Agent 进入一个 UI；hcom 的价值在于保留原 CLI 使用方式，只补通信层。
- `~/.cc-branch/` 可作为全局事件索引，项目内 `.cc-branch/` 保持配置和局部状态。

## 局限和风险

- hook 适配依赖各 Agent CLI 的行为，不同 CLI 的输出、session、resume 机制会变化。
- 消息注入很强，但也容易误触发 Agent 执行高风险操作，需要权限和确认边界。
- relay 模式的密钥和信任模型比较重，不适合作为 CC Branch 的第一阶段能力。

## 可参考实现点

- `HCOM_DIR` 这种目录隔离方式，可借鉴为 CC Branch 的 per-project/global state root。
- 本地 SQLite + WAL 适合做低成本事件日志。
- 命令行层可以先提供 `send`、`watch`、`who`、`screen`、`events` 这类 primitives，再决定是否做 UI。

## 证据来源

- `README.md`
- `src/db/mod.rs`
- `src/hooks/mod.rs`
- `src/router.rs`
- `src/messages.rs`
- `src/relay/crypto.rs`

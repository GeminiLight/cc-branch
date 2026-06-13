<!-- Last verified: 2026-06-12 | Current stage: reference research | Source commit: 638e9c57262179871efad98a073846583ae7cb05 -->

# VibeTree

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [sahithvibudhi/vibe-tree](https://github.com/sahithvibudhi/vibe-tree) |
| 语言 | TypeScript |
| License | MIT |
| GitHub 元数据 | 259 stars；最近 push: 2026-01-02 |
| 一句话定位 | 桌面/Web/Mobile 应用：用多个 git worktree 并行跑 Claude CLI，并保持每个 worktree 的 terminal session。 |

## 解决的问题

`VibeTree` 面向“Claude + 多 worktree + 多端访问”的早期桌面应用。它的 README 明确表示处于活跃开发/重构阶段，稳定桌面版在 `release-v0.1` 分支。

它不是当前最成熟的参考，但作为“worktree terminal desktop”早期形态有价值。

## 架构方案

```text
desktop / web / server
  -> project list
  -> git worktrees
  -> persistent terminal sessions
  -> Claude CLI integration
  -> VS Code / Cursor opener
  -> LAN/mobile access
```

## Worktree 策略

- 用多个 git worktree 表达并行 feature。
- 每个 worktree 有独立 terminal session。
- UI 可以打开 worktree 到 VS Code/Cursor。
- 支持多项目 tab。
- 支持 web/mobile access，通过 WebSocket 连接 server。

## 对 CC Branch 的启发

- **桌面/Web/移动访问是自然需求**：用户希望在手机上看 agent 是否完成。
- **IDE opener 不能缺**：worktree 创建后应能一键用 Cursor/VS Code 打开。
- **多项目 tab 与 worktree session 可以合并在一个 app 中**。

## 局限和风险

- 最近 push 相比其他项目不算活跃。
- README 提示 cloud/multi-platform 正在重构，稳定性需要观察。
- 技术实现文档较少，适合作为形态参考，不适合作为核心架构参考。

## 可参考实现点

- worktree terminal desktop/web/mobile 一体化方向。
- auto-open project 测试入口。
- LAN/mobile WebSocket 访问。
- IDE opener。

## 证据来源

- `README.md`
- `apps/server`
- `apps/web`
- `apps/desktop`

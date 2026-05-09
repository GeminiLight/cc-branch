# CC Branch 功能概览

CC Branch 是一个面向终端 AI 工作流的 CLI-first 工作空间编排器。它不替代 `tmux`，而是把工作空间的定义、启动、恢复、诊断和查看方式统一起来。

## 适合做什么

- **把工作空间写进配置**：用 `.cc-branch.yaml` 描述 slot、window、agent、目录和环境变量。
- **用同一套命令管理全流程**：从 `init`、`plan`、`start` 到 `status`、`doctor`、`session`，入口保持一致。
- **让恢复更稳定**：把本地运行信息写进 `.cc-branch.state.yaml`，回到项目时更容易接上之前的会话。
- **给浏览器一层可视化入口**：除了 CLI，也可以通过内置 Web UI 查看状态、配置和诊断结果。

## 主要功能

### 配置驱动

工作空间结构放在 `.cc-branch.yaml` 里，团队可以共享同一份结构定义，本地运行状态则单独保存在 `.cc-branch.state.yaml`。

你可以在配置里描述：

- `agents` 覆盖，通常可省略，因为内置 agent profile 默认可用
- `slots`
- `windows`
- `cwd`
- `env`
- `display`

### 启动前先预览

`cc-branch plan` 会先把最终结果算出来，再决定要不要启动。

它会帮你确认：

- 每个 slot 会对应哪个 tmux 会话
- 每个 window 最终会执行什么命令
- 哪些 `session_id` 会复用，哪些会自动补齐
- 启动后还会执行哪些附加命令

### 启动与恢复

`cc-branch start` 负责把计划变成实际工作空间，`attach`、`stop`、`restart` 则负责后续操作。

对支持恢复的命令行工具，CC Branch 会结合配置和本地状态，生成更稳定的启动或恢复命令。

### 会话管理

`session` 子命令把会话元数据当成单独对象来管理，而不只是附着在 `status` 输出里。

目前可用的子命令包括：

- `session list`
- `session inspect`
- `session prune`
- `session command`

这对于长期项目尤其有用，因为你可以更清楚地区分正在运行、已经停止和已经孤立的记录。

### 诊断与自动修复

`cc-branch doctor` 用来检查当前环境和配置是否健康，`doctor --fix` 会尝试处理其中一部分低风险问题。

常见检查包括：

- `tmux` 是否可用
- 配置里的命令是否存在
- `cwd` 是否存在
- agent 名称是否可识别
- 需要恢复的窗口是否缺少 `session_id`

### 内置 Web UI

`cc-branch serve` 会启动一个轻量服务，提供浏览器里的查看入口。

它适合用来：

- 查看工作空间状态
- 查看或保存配置
- 查看诊断结果
- 使用内置模板初始化项目
- 使用同一个工具选择器打开工作空间或项目目录
- 适配系统终端、Warp、VS Code、Cursor 等本机工具
- 后台启动、重启、停止 tmux 工作空间或 slot

### 可集成

CC Branch 不只是一个 CLI。当前包也导出了带类型的 Python API，方便桌面包装层、自动化脚本或其他工具直接复用配置装载和计划生成能力。

## 常见使用方式

### 单人开发工作台

一个项目里同时放 planner、coder、review、scratch 等窗口，减少来回手动搭环境的时间。

### 双人或双角色协作

用 `ai-pair` 这类模板快速起一个 coder / reviewer 结构，适合固定分工的协作流程。

### 长期项目

当项目会持续很多天甚至更久时，本地状态和 `session` 管理会明显更有价值，因为你不需要每次都从头整理现场。

### 多项目查看

通过 Web UI 的 `project_path` 覆盖能力，可以把多个项目接到同一套查看入口里。

## 当前重点

现在的产品重点很明确：

- 以 CLI 为主入口
- 以 `tmux` 为实际运行基础
- 以配置文件和本地状态文件作为统一数据源
- 以 session 管理和诊断能力补上长期使用体验

## 当前边界

如果你在评估是否适合自己的流程，下面这些边界也很重要：

- 当前运行仍然建立在 `tmux` 上
- `shell` slot 最终也会归一化成 tmux 里的单窗口结构
- Web UI 已经可用，但它不是独立运行时，只是另一层查看和操作入口
- Wiki 里的旧评审或阶段文档不一定代表当前行为，公开说明以 `docs/` 为准

## 继续阅读

- `docs/getting-started.md`
- `docs/quickstart.md`
- `docs/user-guide.md`
- `docs/architecture.md`
- `wiki/README.md`

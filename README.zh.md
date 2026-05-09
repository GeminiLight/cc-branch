# CC Branch

[English](README.md) | [中文](README.zh.md)

> 用一个项目配置启动和恢复多个 Agent CLI 与 shell 窗口。

CC Branch（`cc-branch`，短别名 `ccb`）是面向 AI 编程工作流的本地工作空间管理工具。它记录窗口布局、Agent 命令、工作目录和本机 session 元数据，让同一套工作环境可以快速重新打开。

## 使用场景

- 将 planner、coder、reviewer、dev server 和 shell 窗口组成一套可重复打开的项目工作台。
- 跨天继续同一个 AI 编程现场，不需要手动重新搭建窗口。
- 团队共享项目工作台模板，同时保留各自本机的 session 状态。

## 功能特色

- **工作台模板**：覆盖 solo、pair、minimal 等常见 AI 编程工作流。
- **启动与连接命令**：预览、启动、连接、停止、重启多个窗口。
- **Session 延续**：为支持恢复的 Agent CLI 保留本机会话信息。
- **本地 Dashboard 与健康检查**：处理初始化、状态查看、配置编辑和常用操作。

## 安装

环境要求：通过 PyPI 或源码安装时需要 Python 3.10+，并安装配置中使用的 Agent CLI。`tmux` 是可选能力，只在使用 `runtime: tmux` 的 slot 时需要。

```bash
pipx install cc-branch
```

或从源码安装：

```bash
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
pip install .
```

源码安装会构建内置 Web UI，因此需要 Node.js/npm。只做 CLI 开发且没有 npm 时，可以使用 `CC_BRANCH_SKIP_WEBUI_BUILD=1 pip install .`；这种安装方式下 `cc-branch serve` 会在构建 Web UI 前不可用。常见安装问题见 `docs/install-troubleshooting.md`。

## 快速开始

最短路径是在项目目录直接启动 Web UI：

```bash
cd /path/to/project
cc-branch serve
```

默认地址：`http://127.0.0.1:8080`

如果项目还没有 `.cc-branch/config.yaml`，Web UI 会引导你创建。

如果你更喜欢命令行流程：

```bash
cc-branch init    # 创建 .cc-branch/config.yaml 和本机状态文件
cc-branch start   # 启动配置中的工作台并进入
```

如果希望 CC Branch 用你选择的本地工具打开工作空间，使用 `cc-branch open`。例如：`cc-branch open --opener warp` 或 `cc-branch open --opener vscode`。

只有在你只想创建可复用的 tmux session、且不想进入工作台或打开 terminal-runtime 窗口时，才使用 `cc-branch start --detach`。

Web UI 里选择一个本地工具后，可以执行“打开工作空间”或“打开项目目录”。终端类工具会在项目目录打开一个交互 shell；VS Code、Cursor 等编辑器会打开项目文件夹。后台启动只用于创建 tmux session，不会弹出可见窗口。

可选检查：

- `cc-branch plan`：启动前预览会创建哪些 session/window。
- `cc-branch doctor`：检查环境和配置中的常见问题。

## 配置示例

```yaml
version: 1
project: "my-app"
root: "."

agents:
  codex:
    command: "codex"

slots:
  - name: "dev"
    windows:
      - name: "planner"
        agent: "codex"
      - name: "server"
        command: "npm run dev"
```

## 更多

项目配置保存在 `.cc-branch/config.yaml`；本机运行状态保存在 `.cc-branch/state.yaml`，通常不提交。更多说明见 `docs/getting-started.md`、`docs/user-guide.md` 和 `docs/features.md`。

## 许可证

本项目采用 MIT 许可证。详情见 [LICENSE](LICENSE)。

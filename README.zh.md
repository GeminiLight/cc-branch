<div align="center">

# CC Branch

### 一键恢复多 Agent CLI 工作台

[English](README.md) | 中文

[![CI](https://github.com/GeminiLight/cc-branch/actions/workflows/ci.yml/badge.svg)](https://github.com/GeminiLight/cc-branch/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-v1.1.0-green)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

CC Branch 恢复一个项目周围的工作环境：Agent、终端、编辑器、本机目录、SSH 机器和可复用会话。

## 为什么用它

### 1. 恢复完整的项目工作台

- 一个项目可能同时需要 Codex、Claude Code、dev server、日志、编辑器和多个 tmux 窗口。
- CC Branch 让这套工作台只配置一次，之后一条命令就能恢复。

### 2. 回到已有会话继续

- 上次开的 Agent 会话和 tmux 会话，很多时候其实还在继续运行。
- CC Branch 可以直接接回这些会话，回到项目就是继续工作，而不是重新开始。

### 3. 同时处理本机和 SSH 机器

- 一个项目可能横跨本机仓库、SSH 机器、GPU 机器、远程 tmux 会话和本机编辑器。
- CC Branch 把本机和远程工作放进同一个 workspace，回到项目就是继续，而不是重新搭环境。

## 安装

### 桌面端

从 [最新 GitHub Release](https://github.com/GeminiLight/cc-branch/releases/latest) 下载桌面端。

需要原生桌面体验时，使用桌面端。

### 用 pip 安装 CLI 和 Web UI

安装 CLI/backend 和打包好的浏览器 Web UI：

```bash
pip install cc-branch
```

pip 包不会安装桌面端。需要原生桌面 App 时，从 GitHub Releases 下载。

### 从源码安装

需要本地开发或查看源码时，可以从仓库安装：

```bash
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
pip install .
```

源码 checkout 不会自动构建 Web UI。开发浏览器 UI 时，先运行 `python scripts/build-webui.py` 再使用 `cc-branch serve`。

`cc-branch` 也可以简写为 `ccb`。

## 快速使用

启动浏览器 Web UI：

```bash
cc-branch service start
```

默认运行在 `http://127.0.0.1:8080`。

在项目里创建并恢复 workspace：

```bash
cd /path/to/project
cc-branch init
cc-branch plan
cc-branch start
```

## 日常命令

| 命令 | 用途 |
| --- | --- |
| `cc-branch service start` | 后台启动本地 Web UI service |
| `cc-branch serve` | 前台运行 Web UI server |
| `cc-branch init` | 创建 starter `.cc-branch/config.yaml` |
| `cc-branch plan` | 启动前展示 Agent、命令、窗格、打开方式和 SSH 目标 |
| `cc-branch start` | 启动缺失目标，或接回可复用的 tmux 会话 |
| `cc-branch attach [tab[:pane]]` | 进入正在运行的 tab、pane 或 tmux target |
| `cc-branch send <tab[:pane]> <message>` | 向正在运行的 tmux 托管 Agent 窗格发送消息 |
| `cc-branch open --opener <tool>` | 用 VS Code、Cursor、Warp、terminal、Web UI 或桌面端打开项目 |
| `cc-branch status` | 查看 runtime 状态 |
| `cc-branch sync` | 把配置变更同步到正在运行的 tmux targets |
| `cc-branch doctor --fix` | 诊断并修复低风险环境、配置或状态问题 |
| `cc-branch session list` | 列出已知 agent session metadata |
| `cc-branch session restore` | 扫描本地 Agent transcript，把可恢复 session 绑定回 pane |
| `cc-branch session hook` | 让 agent-native hook 把 session id 和 transcript 路径写回本地 state |

## 配置示例

```yaml
version: 2
project: my-app
root: .
openWith: cursor
layoutBackend: tmux

tabs:
  - name: agents
    panes:
      - name: planner
        agent: codex
      - name: review
        agent: claude
  - name: remote-lab
    remote:
      host: gpu-dev
      cwd: /srv/my-app
    panes:
      - name: qa
        command: npm run qa
```

内置 agent profiles 会自动可用。只有在需要覆盖内置 profile 或定义自定义本地工具时，才需要添加 `agents` 配置。

## 文档

- [Getting Started](docs/getting-started.md)
- [User Guide](docs/user-guide.md)
- [Feature Reference](docs/features.md)
- [SSH Remote Workspaces](docs/ssh-remote-workspaces.md)
- [Install Troubleshooting](docs/install-troubleshooting.md)
- [Publishing Runbook](docs/publishing.md)

## 🙏 致谢

本项目已发布到 [LINUX DO](https://linux.do/) 社区。我们由衷感谢社区的支持与反馈。

## 许可证

本项目采用 MIT 许可证。详情见 [LICENSE](LICENSE)。

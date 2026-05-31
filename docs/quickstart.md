# 5 分钟快速上手

> 用最短路径把 CC Branch 跑起来。

## 1. 前置要求

你需要：

- 至少一个你会在配置中用到的命令行工具
- 从源码安装当前 CLI 时需要 Python 3.10+
- 只有使用 `layoutBackend: tmux` 时才需要 `tmux`

没有 `tmux` 也可以使用默认的 `layoutBackend: direct`。这种方式会启动普通终端或编辑器里的本地进程，不支持 tmux 的复用、后台生命周期和 tmux 级 attach。

如果想先检查环境，可以运行：

```bash
python3 --version
tmux -V          # 只在你要使用 layoutBackend: tmux 时需要
codex --version   # 或 claude / gemini / cursor 等
```

## 2. 安装

从 PyPI 安装 CLI/backend 和打包好的浏览器 Web UI：

```bash
pip install cc-branch
```

需要源码开发时：

```bash
git clone https://github.com/GeminiLight/cc-branch.git
cd cc-branch
pip install .
```

源码 checkout 不会自动构建 Web UI。需要从源码运行 Web UI 时，在 checkout 里先执行 `python scripts/build-webui.py`。

桌面端通过 GitHub Releases 分发。Homebrew 属于计划中的公开分发渠道；正式可用前不要把 `brew install GeminiLight/cc-branch/cc-branch` 当作当前安装路径。常见安装失败见 `docs/install-troubleshooting.md`。

验证安装：

```bash
cc-branch --help
ccb --help
```

## 3. 初始化工作空间

```bash
cd /path/to/your/project
cc-branch init
```

这一步通常会：

- 检查环境
- 探测本机可用的命令行工具
- 根据默认的 `development` 模板生成起步配置
- 创建 `.cc-branch/state.yaml`
- 自动把本地状态文件加入 `.gitignore`

如果主要做产品/设计工作，可以使用 `--profile design`；如果只需要一个窗格，可以使用 `--profile minimal`。

内置模板：

- `development`
- `design`
- `minimal`

## 4. 先看启动结果

```bash
cc-branch plan
```

重点确认：

- tmux 会话名字是不是你想要的
- 每个标签页和窗格会执行什么命令
- agent session 是自动复用、每次新建，还是显式恢复某个 ID
- 目录、label 和附加命令是否合理

## 5. 启动

```bash
cc-branch start
```

`start` 会按配置创建可复用 tmux 会话或直接启动本地命令，并进入第一个可 attach 的标签页。需要看到总览面板时，显式运行：

```bash
cc-branch dashboard
```

或者：

```bash
cc-branch start --dashboard
```

如果你只想创建可复用的 tmux session，不进入工作台，也不打开 direct 布局的外部进程：

```bash
cc-branch start --detach --prepare
```

如果你想用指定工具打开可见工作空间：

```bash
cc-branch open --opener warp
cc-branch open --opener vscode
cc-branch open dev:planner --opener cursor
```

## 6. 日常命令

```bash
cc-branch status
cc-branch attach dev
cc-branch attach dev:planner
cc-branch doctor --fix
cc-branch session list
cc-branch session inspect dev:planner
```

清理孤立记录：

```bash
cc-branch session prune --dry-run
cc-branch session prune
```

输出恢复命令：

```bash
cc-branch session command dev:planner
```

## 7. 打开 Web UI

```bash
cc-branch service start
```

默认地址：

- `http://127.0.0.1:8080`

`cc-branch service start` 是本机 app 级服务，不会因为你站在某个目录里就创建 `.cc-branch/`。你可以在 Web UI 里添加项目，或者之后显式执行 `cc-branch init`；只有这些项目级动作才会写入项目目录。`cc-branch serve` 仍然可用，但它是前台服务，会在你按 `Ctrl+C` 或关闭终端后停止。

如果要绑定到非本机地址，请使用 `--token` 或设置 `CC_BRANCH_WEB_TOKEN`。启用 token 后，第一次打开服务端打印的 `/?token=...` 链接来建立浏览器 cookie。

你可以用它来：

- 查看状态
- 查看或保存配置
- 查看诊断结果
- 用模板初始化工作空间
- 用同一个工具选择器打开工作空间或项目目录
- 后台启动、重启、停止 tmux 工作空间或标签页

Web UI 里有一个工具选择器和两个动作：“打开工作空间”和“打开项目目录”。打开工作空间会按工具适配：Terminal.app、iTerm2 等终端运行 dashboard/attach；Warp 使用稳定的 Launch Configuration 打开布局；VS Code、Cursor 会正常打开项目目录，并通过 `.vscode/tasks.json` 的 folder-open tasks 创建 integrated terminal 来运行 workspace 命令。打开项目目录始终用系统文件管理器，让用户进入普通文件夹视图。`layoutBackend: tmux` 的标签页可复用；从另一个 Terminal、Warp、VS Code 或 Cursor 再打开时会 attach 到同一组 session。`layoutBackend: direct` 的窗格是外部进程，再次打开就是新的本地进程。“后台启动”只创建 tmux 会话，不会弹出窗口。

## 8. 记住这两个文件

- `.cc-branch/config.yaml`：项目配置，可以提交到仓库
- `.cc-branch/state.yaml`：本地状态文件，通常不建议提交

## 9. 接下来读什么

- `docs/user-guide.md`
- `docs/features.md`
- `docs/architecture.md`

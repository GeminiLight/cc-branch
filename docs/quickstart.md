# 5 分钟快速上手

> 用最短路径把 CC Branch 跑起来。

## 1. 前置要求

你需要：

- 至少一个你会在配置中用到的命令行工具
- 只有通过 PyPI 或源码安装时才需要 Python 3.10+
- 只有使用 `runtime: tmux` 时才需要 `tmux`

没有 `tmux` 也可以使用 `runtime: terminal`，只是不支持 tmux 的复用、后台生命周期和 dashboard 能力。

如果想先检查环境，可以运行：

```bash
python3 --version
tmux -V          # 只在你要使用 runtime: tmux 时需要
codex --version   # 或 claude / gemini / cursor 等
```

## 2. 安装

Homebrew tap 发布后，macOS / Linux 推荐：

```bash
brew install GeminiLight/cc-branch/cc-branch
```

Python 用户推荐用 `pipx`：

```bash
pipx install cc-branch
```

只在虚拟环境里使用 `pip install cc-branch`。

从源码安装会构建 Web UI，需要 Node.js/npm；常见安装失败见 `docs/install-troubleshooting.md`。

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
- 根据默认的 `solo-dev` 模板生成起步配置
- 创建 `.cc-branch/state.yaml`
- 自动把本地状态文件加入 `.gitignore`

只有在你想选择其他模板时，才需要使用 `--profile ai-pair` 或 `--profile minimal`。

内置模板：

- `solo-dev`
- `ai-pair`
- `minimal`

## 4. 先看启动结果

```bash
cc-branch plan
```

重点确认：

- tmux 会话名字是不是你想要的
- 每个窗口会执行什么命令
- `session_id` 是复用还是新生成
- 目录、label 和附加命令是否合理

## 5. 启动

```bash
cc-branch start
```

`start` 会创建 tmux 会话和窗口，并进入第一个 slot。需要看到总览面板时，显式运行：

```bash
cc-branch dashboard
```

或者：

```bash
cc-branch start --dashboard
```

如果你只想创建可复用的 tmux session，不进入工作台，也不打开 `runtime: terminal` 外部窗口：

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
cc-branch serve
```

默认地址：

- `http://127.0.0.1:8080`

也可以先不运行 `cc-branch init`，直接在项目目录执行 `cc-branch serve`；Web UI 会显示 setup 流程，并在你选择模板后创建配置。

如果要绑定到非本机地址，请使用 `--token` 或设置 `CC_BRANCH_WEB_TOKEN`。启用 token 后，第一次打开服务端打印的 `/?token=...` 链接来建立浏览器 cookie。

你可以用它来：

- 查看状态
- 查看或保存配置
- 查看诊断结果
- 用模板初始化工作空间
- 用同一个工具选择器打开工作空间或项目目录
- 后台启动、重启、停止 tmux 工作空间或 slot

Web UI 里有一个工具选择器和两个动作：“打开工作空间”和“打开项目目录”。打开工作空间会按工具适配：Terminal.app、iTerm2 等终端运行 dashboard/attach；Warp 使用 Launch Configuration 打开布局；VS Code、Cursor 像普通打开项目一样直接打开目录，不生成临时 `.code-workspace`。打开项目目录使用同一个所选工具：终端类工具会在项目目录打开一个交互 shell，编辑器类工具会打开项目文件夹。tmux 工作空间可复用；从另一个 Terminal、Warp 或 iTerm2 再打开时会 attach 到同一组 session。传统 `runtime: terminal` 不可复用，再次打开就是新的外部进程。“后台启动”只创建 tmux 会话，不会弹出窗口。

## 8. 记住这两个文件

- `.cc-branch/config.yaml`：项目配置，可以提交到仓库
- `.cc-branch/state.yaml`：本地状态文件，通常不建议提交

## 9. 接下来读什么

- `docs/user-guide.md`
- `docs/features.md`
- `docs/architecture.md`
- `wiki/README.md`

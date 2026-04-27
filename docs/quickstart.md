# 5 分钟快速上手

> 用最短路径把 CC Branch 跑起来。

## 1. 前置要求

你需要：

- `tmux`
- 至少一个你会在配置中用到的命令行工具
- 只有通过 PyPI 或源码安装时才需要 Python 3.10+

Windows 下请先通过 WSL、MSYS2 或 Cygwin 提供可用的 `tmux`。

如果想先检查环境，可以运行：

```bash
python3 --version
tmux -V
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
- 创建 `.cc-branch.state.toml`
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

如果你只想后台启动，不打开任何可见面板：

```bash
cc-branch start --detach --prepare
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
- 在本机系统终端打开 workspace dashboard 或某个 slot
- 在 VS Code、Cursor 等编辑器中打开项目目录
- 后台启动、重启、停止工作空间或 slot

Web UI 里“在终端打开工作空间”会让本机后端打开一个系统终端并运行 `cc-branch dashboard`；Open With 可以选择 VS Code / Cursor 打开项目目录；“后台启动”只创建 tmux 会话，不会弹出窗口。

## 8. 记住这两个文件

- `.cc-branch.yaml`：项目配置，可以提交到仓库
- `.cc-branch.state.toml`：本地状态文件，通常不建议提交

## 9. 接下来读什么

- `docs/user-guide.md`
- `docs/features.md`
- `docs/architecture.md`
- `wiki/README.md`

# Workspace 术语规范

状态：草案，用于 Web UI、配置编辑器和后续配置模型重构。

这份文档定义 CLI Workspace 里“工作空间、标签页、窗格、终端会话、Agent”等概念。目标是让产品界面、配置文件、运行时实现使用同一套心智模型。

## 标准层级

```text
Workspace / 工作空间
└─ Tab / 标签页
   └─ Pane / 窗格
      └─ Terminal Session / 终端会话
         └─ Agent / Command / Agent 或命令
```

一句话版本：

- **Workspace** 是整个项目的命令行工作台。
- **Tab** 是工作台里可切换的一组上下文。
- **Pane** 是 Tab 里被分屏出来的一个区域。
- **Terminal Session** 是 Pane 里真正运行的终端状态。
- **Agent / Command** 是终端会话里启动的东西。

## 用户可见术语

| 英文 | 中文 | 一句话定义 | 用户是否应该看到 |
|---|---|---|---|
| Workspace | 工作空间 | 当前项目的一套命令行工作台，包括布局、终端、Agent 和运行状态。 | 是 |
| Canvas | 画布 | 可视化展示和编辑 Workspace 布局的界面区域。 | 是 |
| Tab | 标签页 | Workspace 内的一组工作上下文，例如 Coding、Review、Servers。 | 是 |
| Pane | 窗格 | Tab 内的一个分屏区域，可以放一个终端会话，也可以未来放日志、预览、Diff。 | 是 |
| Terminal Session | 终端会话 | Pane 背后的运行状态，包括 cwd、shell、命令、进程、resume id。 | 低频展示 |
| Agent | Agent | 可复用的 AI CLI 工具或角色，例如 Codex、Claude、Gemini。 | 是 |
| Command | 命令 | 在终端会话里执行的 shell 命令。 | 是 |
| Split | 分屏 | Pane 之间的布局关系，例如左右分屏、上下分屏、网格。 | 是 |
| Project | 项目 | 侧边栏里注册的本地目录；一个项目可以有一个或多个 workspace 配置。 | 是 |
| Config | 配置 | 保存 Workspace 定义的 YAML 文件。 | 低频展示 |
| State | 状态 | 本地运行时元数据，例如 session id、label、启动状态。 | 诊断场景展示 |
| Opener | 打开方式 | 用哪个工具打开 Workspace，例如 Warp、Terminal、VS Code、Cursor。 | 是 |

## 核心概念

### Workspace / 工作空间

Workspace 是产品的主对象，不是 VS Code 的 `.code-workspace` 文件。

它回答的问题是：

- 这个项目打开后应该有哪些标签页？
- 每个标签页里应该如何分屏？
- 每个窗格里跑什么 Agent 或命令？
- 使用哪些全局默认值，哪些在当前工作空间覆盖？

示意：

```text
Workspace: cli-workspace
├─ Tab: Coding
├─ Tab: Review
└─ Tab: Servers
```

### Canvas / 画布

Canvas 是 UI 表达，不一定是配置文件里的一级对象。

它负责把 Workspace 的结构直接画出来：

```text
Workspace Canvas

┌─────────────────────────────────────────┐
│ Tab: Coding                             │
│ ┌──────────────────┬──────────────────┐ │
│ │ Pane: Builder    │ Pane: Reviewer   │ │
│ │ Codex            │ Claude           │ │
│ └──────────────────┴──────────────────┘ │
└─────────────────────────────────────────┘
```

推荐交互：

- 点击 Tab，编辑标签页名称、默认目录、打开方式。
- 点击 Pane，编辑 Agent、命令、cwd、resume session。
- 拖动或按钮操作改变 Split。
- 低频配置放在详情区或折叠区，不压过 Canvas。

Canvas 必须同时表达两层结构：

```text
Workspace Canvas
├─ Tab rail: Coding / Review / Servers / Scratch
└─ Active Tab layout
   ├─ Pane: Builder
   ├─ Pane: Reviewer
   └─ Pane: Shell
```

也就是说，Canvas 不是简单的“终端卡片列表”。它要让用户一眼区分：

- 当前在编辑哪个 **Tab**，也就是哪个工作上下文。
- 当前选中了哪个 **Pane**，也就是哪个分屏区域。
- 这个 Pane 里绑定了哪个 **Terminal Session** 或内容。

推荐 Canvas 结构：

| 区域 | 作用 |
|---|---|
| Tab rail | 切换、添加、重命名、排序 Tab。 |
| Pane layout | 展示当前 Tab 内部的分屏结构。 |
| Inspector | 编辑选中的 Tab 或 Pane。 |
| Scheduling actions | Move、Split、Duplicate、Pin、Open in opener。 |
| Inherited globals | 展示默认 opener、默认 shell、Agent 模板来源。 |

Canvas 的调度能力应该围绕 Pane 设计：

- 把 Pane 从 `Coding` 移到 `Review`。
- 把一个 Pane 左右或上下拆分。
- 复制 Pane，保留相同 Agent 但换 cwd 或 session。
- 固定某个 Pane，让它在多个 Tab 里可见。
- 选择用 Warp、VS Code、Cursor 或普通 Terminal 打开这个 Pane。

### Tab / 标签页

Tab 是 Workspace 内的一组工作上下文。用户通过 Tab 切换不同任务视角。

例子：

- `Coding`：Builder + Reviewer 两个窗格。
- `Servers`：Web dev server + backend server 两个窗格。
- `Scratch`：一个普通 shell。
- `Review`：review agent + test runner。

Tab 可以包含一个 Pane，也可以包含多个 Pane。

```text
Tab: Coding
├─ Pane: Builder
└─ Pane: Reviewer
```

### Pane / 窗格

Pane 是 Tab 内的分屏区域。它是结构概念，不等于终端本身。

Pane 可以承载：

- 终端会话
- 日志视图
- 预览
- Diff
- Agent 状态
- Scratch notes

第一版可以只支持终端会话，但术语上不要把 Pane 直接叫成 Terminal。这样以后扩展不会被“终端”这个词锁死。

```text
Pane: Builder
└─ Terminal Session
   ├─ agent: Codex
   ├─ cwd: ./apps/web
   └─ command: codex resume ...
```

### Terminal Session / 终端会话

Terminal Session 是运行时概念。它描述 Pane 里真正启动的终端状态。

它通常包括：

- shell：`zsh`、`bash`、`powershell`
- cwd：工作目录
- command：启动命令
- agent：绑定的 Agent
- resume session id：Agent 的恢复会话
- process status：运行中、已停止、失败

UI 里不需要频繁暴露完整术语。多数时候可以显示为：

- 运行中
- Codex
- `~/code/cli-workspace`
- session id 可选

## 推荐 UI 文案

使用这些文案：

- 打开工作空间
- 添加标签页
- 重命名标签页
- 拆分窗格
- 添加窗格
- 选择 Agent
- 设置启动命令
- 绑定会话
- 选择打开方式
- 编辑全局默认值

避免这些文案：

- 添加 Slot
- 添加 Window
- 打开 window
- Pane 终端
- Workspace 文件

## 配置文件映射

YAML 公开格式使用 `tabs` 和 `panes`，不再让用户理解旧的 slot/window 命名。

```yaml
version: 2
project: cli-workspace
root: .

tabs:
  - name: coding
    layout: horizontal
    panes:
      - name: spec
        agent: codex
      - name: review
        agent: claude
```

普通 pane 默认就是 terminal pane。只有 tmux 需要局部展开：

```yaml
tabs:
  - name: dev
    panes:
      - name: tmux-dev
        runtime: tmux
        windows:
          - name: shell
            command: zsh
          - name: server
            command: npm run dev
```

| 配置字段 | 产品名 | 说明 |
|---|---|---|
| tabs | Tab / 标签页 | 一组工作上下文。 |
| panes | Pane / 窗格 | 标签页内的分屏区域。 |
| runtime | 运行方式 | 属于 pane；默认是 terminal，tmux 需要显式写。 |
| windows | Tmux windows | 只在 `runtime: tmux` 的 pane 内部出现。 |
| agents | Agent 模板 | 全局或项目级 Agent 覆盖，不和当前 workspace 的 pane 编辑混在一起。 |

迁移期间可以采用：

```text
Backend/config: slot.window
Product UI: Tab > Pane
```

也就是说，内部可以暂时不改名，但用户界面不要继续显示 `Slot` 和 `Window`。

## 和外部工具的映射

不同终端工具的原生概念不完全一致。产品术语应该保持稳定，由 opener 负责映射。

| 产品概念 | tmux | Warp | VS Code / Cursor | 普通 Terminal |
|---|---|---|---|---|
| Workspace | 一组 tmux session 或一个主 session | 一个 launch config 启动的工作台 | 打开的项目目录 + 集成终端 | 打开的项目目录 + 外部终端进程 |
| Tab | tmux window | Warp tab | 终端 tab / terminal group | 独立终端窗口或 tab |
| Pane | tmux pane | Warp pane | split terminal pane | 通常退化为一个窗口或 tab |
| Terminal Session | shell 进程及其状态 | pane 内 shell 进程 | integrated terminal session | shell 进程 |
| Agent / Command | pane 内命令 | pane 内命令 | terminal 内命令 | terminal 内命令 |

注意：

- `Tab` 是产品概念，不强制等同于浏览器 tab 或系统窗口。
- `Pane` 是分屏区域，不强制等同于终端进程。
- opener 可以根据工具能力降级。例如普通 Terminal 不支持真实 split 时，可以把多个 Pane 打开成多个窗口或 tab。

## 全局配置和 Workspace 配置

不要把全局信息塞进 Workspace Config 的主编辑区。

推荐边界：

| 位置 | 放什么 |
|---|---|
| Workspace Config | 当前 Workspace 的 Tab、Pane、Split、workspace-level overrides |
| Settings | Projects、全局 Agent 模板、默认 opener、默认 shell |
| Dashboard | 状态、启动、停止、打开工作空间 |
| Diagnostics | 环境检测、缺失能力、启动失败原因 |

Workspace 页面可以展示全局继承摘要，但不要直接铺开全局表单。

示例：

```text
Inherited Globals
├─ Default opener: Warp
├─ Default shell: zsh
└─ Agent templates: Codex, Claude
```

需要编辑时跳到 Settings。

## 目标配置形态

下面是目标术语下的配置示意，不代表当前已实现 schema。

```yaml
workspace:
  name: cli-workspace
  root: .

tabs:
  - name: Coding
    layout: vertical
    panes:
      - name: Builder
        agent: codex
        cwd: .
        resume_session: 019f...
      - name: Reviewer
        agent: claude
        cwd: .

  - name: Servers
    layout: vertical
    panes:
      - name: Web
        command: npm run dev
        cwd: apps/web
      - name: API
        command: python -m cc_branch.web
        cwd: .
```

## 最终原则

1. 用户看到的是 `Workspace > Tab > Pane`，不是 `Slot > Window`。
2. `Pane` 是结构区域，`Terminal Session` 是运行状态。
3. `Agent` 和 `Command` 是 Pane 里启动的内容，不是布局对象。
4. `Canvas` 必须区分 Tab 和 Pane：Tab 是上下文，Pane 是可调度区域。
5. `Canvas` 是编辑体验，不是必须写进配置的对象。
6. 全局默认值展示为继承摘要，真正编辑放在 Settings。

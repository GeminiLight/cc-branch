# CC Branch 当前产品审查报告

日期：2026-05-13
范围：当前工作树下的 Web UI、配置模型、Dashboard / Space canvas / Project config / Doctor 主流程。

## 审查方式

- 启动当前代码后端：`./bin/cc-branch serve --host 127.0.0.1 --port 5194`
- 启动当前代码前端：`CC_BRANCH_API_TARGET=http://127.0.0.1:5194 npm run dev -- --host 127.0.0.1 --port 5182`
- 浏览器走查：Dashboard、Space canvas、Project config、Doctor、移动端 Dashboard。
- 接口核对：`/api/config`、`/api/status`。
- 自动验证：
  - `npm run lint`
  - `npm test`
  - `npm run build`
  - `python -m unittest discover tests`

截图保存在：

- `tmp/review-screenshots-current/dashboard.png`
- `tmp/review-screenshots-current/workspace.png`
- `tmp/review-screenshots-current/project.png`
- `tmp/review-screenshots-current/doctor.png`
- `tmp/review-screenshots-current/mobile-dashboard.png`

## 总体判断

测试和构建是通过的，但当前产品还不是“用户能放心用”的状态。主要问题不在单个页面好不好看，而在几个核心心智没有完全对齐：

- Dashboard、Space canvas、Project config 对同一份配置的计数和表达不一致。
- Sidebar 状态复用了 Dashboard 的 query key，但两边期望的数据结构不同，会直接显示 `undefined/undefined · Error loading workspace`。
- Space canvas 的术语和微文案还不够精确，尤其是 tmux group / terminal pane 的层级表达。
- Project config 仍然暴露了容易误解的全局字段，让用户以为自己在改当前工作空间的布局。

当前 UX 分数：6.5/10。视觉基础比之前稳定，但功能状态、术语一致性、信息架构还需要继续打磨。

## P0 功能问题

### 1. Sidebar 状态缓存冲突，显示 `undefined/undefined · Error loading workspace`

证据：

- 当前页面在 Dashboard、Space canvas 中都出现过 Sidebar 文案：`undefined/undefined · Error loading workspace`。
- `Sidebar` 把自己的项目状态查询 key 改成了 `["workspace", "status", p.path, p.selected_config_path]`，这个 key 和 `useWorkspace` 完全相同。
- 但 `useWorkspace` 缓存的是完整 `WorkspaceStatus`，`Sidebar` 期望的是 `{ status, runningCount, totalCount }`。

相关代码：

- `apps/web/src/components/Sidebar.tsx:110-137`
- `apps/web/src/components/Sidebar.tsx:254-257`
- `apps/web/src/hooks/useWorkspace.ts:9-15`

影响：

- 用户刚进入应用就看到错误状态，即使主内容区其实可以加载。
- 这会直接破坏用户对“当前工作空间到底有没有跑起来”的判断。
- Doctor 可能显示全绿，但 Sidebar 显示 Error，形成互相矛盾的状态。

建议：

- 不要用同一个 query key 存不同 shape 的数据。
- 如果要复用 workspace status cache，Sidebar 应该直接读取完整 `WorkspaceStatus` 并在渲染时派生 `runningCount / totalCount`。
- 或者保留独立 key，例如 `["sidebar", "project-status", ...]`，但通过 `queryClient.getQueryData(["workspace", "status", ...])` 做初始值。

## P1 功能 / 信息架构问题

### 2. Space canvas 顶部计数错误：`2 tabs / 2 panes`，但实际是 3 panes

证据：

- Dashboard 显示：`2 tabs · 3 panes`。
- Space canvas 顶部显示：`2 tabs / 2 panes`。
- 当前配置中 `codex-spec` 有 2 个 terminal panes，`tmux-dev` 有 1 个 tmux pane，总数应该是 3。

相关代码：

- `apps/web/src/components/ConfigEditor/index.tsx:365-367`
- `apps/web/src/components/ConfigEditor/index.tsx:497-500`

根因：

`configuredWindowCount` 对 terminal tab 只加 1：

```ts
slot.runtime === "terminal" ? 1 : slot.windows.length
```

这和现在的术语模型冲突。terminal tab 也可以有多个 panes，因此应按 `slot.windows.length` 计数。

影响：

- 用户无法相信画布摘要。
- 这会加重“Tab / Pane / tmux group”本来就复杂的心智负担。

### 3. Project config 的 `Layout backend: Direct` 会误导用户

证据：

- 当前配置里第二个 tab 是 `layoutBackend: tmux`。
- `/api/status` 正确解析为 `tmux-dev runtime: tmux`。
- 但 Project config 页面仍显示一个很突出的 `LAYOUT BACKEND Direct`。

相关代码：

- `cc_branch/models/config.py:276-285`
- `apps/web/src/components/ConfigEditor/index.tsx:492-510`
- `apps/web/src/components/ConfigEditor/ProjectSection.tsx`

判断：

这个字段现在表达的是“全局默认 layout backend”，不是当前 workspace 里所有 tab 的真实状态。放在 Project config 顶层会让用户误以为整个 workspace 都是 Direct。

建议：

- Project config 中不要把全局 `layoutBackend` 当核心字段展示。
- 如果保留，应改名为“默认承载方式”，并放到高级设置。
- 当前 workspace 的真实承载情况应该只在 Space canvas / Dashboard 中表达。

### 4. Dashboard、Space canvas 对 tmux group 的表达仍不统一

证据：

- Dashboard：`tmux-dev` 显示 `1 terminal · 1 panes`，下面又显示 `Tmux pane`、`TMUX-MANAGED PANES`。
- Space canvas：显示 `TMUX-MANAGED PANE STACK`，同时又说 `1 panes managed by tmux`。

影响：

- 用户很难形成稳定概念：到底这是一个 terminal、一个 pane、一个 tmux group，还是一个 tmux session。
- 复数错误 `1 panes` 也会降低精致感。

建议：

- 固定概念层级：
  - Tab：外部工具里的标签页 / 工作区。
  - Pane：Tab 里的一个可视终端区域。
  - Tmux group：一个 Pane 内部由 tmux 管理的一组 windows。
  - Tmux window：tmux group 内部的可切换窗口。
- Dashboard 卡片建议显示为：
  - `TAB tmux-dev`
  - `1 tmux group`
  - group 内：`1 tmux window · running`
- Space canvas 里 tmux group 应作为一个可拖拽的 group block，而不是混成普通 pane 的样式。

## P1 UI/UX 问题

### 5. Space canvas 的信息密度和视觉层级仍然偏“工程调试面板”

证据：

- 页面里同时出现顶部摘要、canvas 标题、tab 卡片、pane 卡片、右侧 inspector。
- 视觉上有较多浅色块嵌套，边界线、浅背景、标签、小图标同时存在。
- 用户第一眼最应该看到的是“最终会打开成什么样”，但当前第一视觉仍是配置编辑器。

建议：

- Canvas 区域应该更像真实运行预览：tab 是容器，pane/group 是主要对象。
- 右侧 inspector 保留，但默认只显示选中对象的核心字段。
- 次要说明文字继续减少，例如 “Tabs are containers...” 这类解释可以放 tooltip 或空状态，不应长期占首屏。

### 6. 画布内操作控件过小，动作语义不够直觉

证据：

- 每个 tab 行右侧有 `+`、删除、拖拽等小图标。
- pane 卡片上也有拖拽点，但主操作不明显。
- 可拖动、可选中、可移动到其他 tab 之间缺少稳定的视觉状态语言。

建议：

- 选中态用外层描边和轻背景，不要额外加明显按钮。
- 拖拽把手可以只在 hover 时显示，但 hover 时要配 tooltip。
- “新增 pane”最好是出现在 tab 内空位或末尾的 `+ Pane` slot，而不是只放在行右上角。
- 跨 tab 移动应支持直接拖拽；右侧 inspector 的 move 只作为精确操作补充。

### 7. Dashboard 首屏行动区语义还可以再合并

证据：

- 当前右上有 `Open directory`、`Refresh status`、opener selector、`Launch`。
- 这比之前清晰，但仍然把“环境选择”和“启动”放在了较窄的一排控件里。

建议：

- 保持顺序：`Open directory` / `Refresh status` 作为轻量工具；`[System Terminal ▾][Launch]` 作为主动作组。
- 主动作组应该比工具按钮更靠右、更重；工具按钮可以更轻，避免用户把 Open directory 当主流程。
- 如果 selected opener 不支持 workspace launch，主按钮应显示明确不可用原因，而不是只 disabled。

## P2 文案 / 国际化问题

### 8. 仍有裸 key 显示：`SLOTSTITLE`、`configureInConfigTab`

证据：

- Space canvas 顶部出现 `SLOTSTITLE`。
- Dashboard 空态曾出现 `configureInConfigTab`。

相关代码：

- `apps/web/src/components/ConfigEditor/index.tsx:497`
- `apps/web/src/components/Dashboard.tsx:730`
- `apps/web/src/i18n/index.tsx`

建议：

- 给 `slotsTitle`、`configureInConfigTab` 补全中英文。
- 增加一个 i18n test：扫描 `t("...")` 调用，至少覆盖核心页面 key 是否存在。

### 9. Doctor 页面过于乐观，没有反映配置/UI 状态冲突

证据：

- Doctor 显示 `All checks passed`。
- 但同一时间 Sidebar 可以显示 Error，Space canvas 存在计数错误，Dashboard/Config 有概念不一致。

判断：

Doctor 现在更像 CLI 环境检查，不像产品级健康检查。它不需要覆盖全部 UI 问题，但至少应该能提示“当前 config 有 runtime/state 不一致、未知字段、项目状态加载失败”等真实用户会遇到的问题。

建议：

- Doctor 分成三类：Environment、Config、Runtime。
- Config 类应读取和 Config 页面同一套 validation 结果。
- Runtime 类应展示 tmux current/changed/missing/extra/orphaned 的摘要。

## 通过项

- 当前代码验证通过：
  - `npm run lint`
  - `npm test`：18 files / 110 tests
  - `npm run build`
  - `python -m unittest discover tests`：374 tests
- 当前后端代码可以正确识别 `layoutBackend: tmux`，`tmux-dev` 在 `/api/status` 中为 `runtime: tmux`。
- Space canvas 已经比之前更接近“所见即所得”，尤其是 terminal panes 和 tmux group 的基础结构已经出现。
- Dashboard 的主动作组比之前更克制，方向是对的。

## 推荐修复顺序

1. 先修 Sidebar query key / cache shape 冲突。这是当前最像真实 bug 的问题。
2. 修 Space canvas 计数和 i18n 裸 key。
3. 统一 Dashboard / Space canvas 的 tmux group 文案和计数。
4. 调整 Project config，把全局默认字段降级到高级设置。
5. 再打磨画布交互：选中态、拖拽态、跨 tab 移动、tmux group 内 window 编辑。

## 结论

当前产品不是“功能不可用”，但还没有达到“用户一看就懂、一用就稳”的标准。最值得马上处理的是状态一致性和概念一致性：同一份配置在不同页面必须说同一种话、算出同一个数、给出同一个运行判断。UI 继续优化前，应先把这条底线修牢。

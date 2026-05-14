# CC Branch 当前代码与产品审查报告

日期：2026-05-14
范围：当前工作树下的配置模型、Web UI Dashboard / Project config / Doctor 主流程、前后端验证路径。

## 审查目标

这轮审查按三个要求执行：

- 架构质量：配置模型、运行时 adapter、前端展示层是否对同一套概念保持一致。
- 功能正确性：找出会误导用户或导致错误诊断的真实 bug，并补测试。
- UI/UX 精修：减少首屏误解、状态误报和控件截断，让用户更容易理解“当前工作空间到底会怎么启动”。

## 当前结论

整体质量比上一轮稳定，但还不能说完全完成。核心进展是把配置 v2 的公共字段、agent adapter 枚举、诊断页展示规则重新对齐，并对 Dashboard 的主动作区做了窄幅修复。

当前产品风险从“明显显示错误状态”下降到“仍需要持续打磨复杂配置体验”。本轮已修复的问题都有测试或接口证据覆盖。

## 已确认并修复的问题

### 1. 配置校验和运行时 adapter 枚举不一致

问题：

- agent adapter 实际支持 `resume_mode: internal` 和 `label_mode: internal`。
- 前端和 `agents.yaml` 也按 `internal` 表达。
- 但配置校验常量仍接受 `command`，拒绝 `internal`。

影响：

- 合法配置会被误报 invalid enum。
- 非运行时支持的 `command` 值反而可能通过校验。

修复：

- `cc_branch/application/config_validation/constants.py`
  - `RESUME_MODES = {"none", "flag", "internal"}`
  - `LABEL_MODES = {"none", "metadata", "internal"}`
- `tests/test_application_architecture.py`
  - 新增 `test_collect_config_issues_uses_runtime_agent_adapter_enums`
  - 覆盖 `internal` 被接受、`command` 被拒绝。

### 2. `openWith` / `layoutBackend` 被旧路径误报 unknown field

问题：

- 当前后端已经接受 `openWith` 和 `layoutBackend`。
- 但诊断页直接渲染 `configData.issues`，没有复用配置页的 stale warning 过滤逻辑。
- 如果浏览器或 React Query cache 中残留旧后端返回的 warning，诊断页仍会展示：
  - `Unknown field 'openWith'`
  - `Unknown field 'layoutBackend'`

影响：

- 用户会以为当前配置格式仍然不合法。
- Configuration / Doctor 两个页面对同一配置给出不同判断。

修复：

- `apps/web/src/utils/configIssues.ts`
  - 新增共享 `visibleConfigIssues()`。
  - 只过滤已确认属于 v2 公共字段的 stale unknown warning。
  - 其他真实 unknown field 仍正常展示。
- `apps/web/src/components/ConfigEditor/index.tsx`
  - 改为使用共享 helper。
- `apps/web/src/components/DoctorView.tsx`
  - 诊断页也使用同一套展示规则。
- `apps/web/src/components/DoctorView.test.tsx`
  - 新增测试：过滤 `openWith` / `layoutBackend`，保留真实 `stillWrong`。

验证：

- 当前接口 `GET /api/config?project_path=/Users/geminilight/code/cli-workspace` 返回 `issues: []`。
- 配置页与诊断页都有对应测试覆盖。

### 3. 混合 tab 的 YAML round-trip 缺少保护

问题：

- 当前配置模型允许一个 tab 下同时存在普通 terminal pane 和 tmux window group。
- 这是近期明确下来的核心概念，但 YAML parse / serialize 没有专门测试保护。

影响：

- 后续改 UI 或 serializer 时，容易把 tmux group 内部 windows flatten 掉。
- 用户在画布里编辑复杂布局后可能丢结构。

修复：

- `apps/web/src/components/ConfigEditor/yaml-utils.test.ts`
  - 新增 round-trip 测试。
  - 覆盖一个 tab 内同时存在 direct pane 和 `layoutBackend: tmux` group。
  - 验证 tmux group 内部 windows 在 serialize / reparse 后仍保留。

### 4. Dashboard 主动作区控件宽度和换行问题

问题：

- `System Terminal` 在 Dashboard 右上主动作组里容易被截断。
- `Open directory` / `Refresh status` 在窄宽度下会换行，导致按钮高度和视觉节奏不一致。
- `Launch` 宽度偏紧。

影响：

- 用户第一眼看不清“先选环境，再启动”的主流程。
- 主动作区显得不够精致。

修复：

- `apps/web/src/components/Dashboard.tsx`
  - opener selector 宽度从 `112/132px` 调整为 `136/168px`。
  - 工具按钮和启动按钮增加 `whitespace-nowrap`。
  - 启动按钮最小宽度提高到 `96px`。

验证：

- 截图证据：
  - `tmp/review-pass/dashboard-after-actions.png`
  - `tmp/review-pass/dashboard-after-width.png`

### 5. tmux 文案的中英文词典混用

问题：

- 英文词典中的 `tmuxPanes` 曾被误改为中文。
- 中文词典中的 `tmuxWindows` / `tmuxPanes` 仍保留英文表达。

影响：

- 切换语言时，Dashboard 和画布中 tmux group / tmux window 的词汇会混杂。
- 这会放大本来就复杂的 Tab / Pane / Tmux group 概念负担。

修复：

- `apps/web/src/i18n/index.tsx`
  - 英文保持 `Tmux windows`。
  - 中文统一为 `Tmux 窗口`。

验证：

- `cd apps/web && npm test -- Dashboard.test.tsx DoctorView.test.tsx ConfigEditor.test.tsx`
- `cd apps/web && npm run lint`

### 6. Project config 暴露工程化术语

问题：

- 表单里仍出现 `Layout backend` 这类实现术语。
- 用户真正需要理解的是“这个窗格会作为普通终端打开，还是作为 tmux 窗格组打开”。

影响：

- 用户会把底层 YAML 字段理解成产品概念。
- Project config 看起来更像内部调试面板，而不是可用的配置界面。

修复：

- `apps/web/src/i18n/index.tsx`
  - `Layout backend` 改为 `Pane type`。
  - `Default layout backend` 改为 `Default pane type`。
  - `Direct` 改为 `Regular terminal`。
  - 中文统一为 `窗格类型`、`默认窗格类型`、`普通终端`、`Tmux 窗格组`。

### 7. 空间画布把 tmux windows 误计为 panes

问题：

- 一个 tmux group 在外部空间里应该占一个 pane。
- tmux group 内部可以包含多个 tmux windows。
- 空间画布和配置摘要有路径使用 `slot.windows.length` 计数，legacy tmux tab 会被误算成多个 panes。

影响：

- 用户看到的摘要和实际画布结构不一致。
- 对 “Tab / Pane / Tmux group / Tmux window” 的概念理解会被进一步干扰。

修复：

- `apps/web/src/components/ConfigEditor/index.tsx`
  - 新增 `configuredPaneCount()`，把 legacy tmux slot 计为 1 个 pane。
- `apps/web/src/components/ConfigEditor/SlotsSection.tsx`
  - 空间画布摘要改用 `paneCount(slot)`。
- `apps/web/src/i18n/index.tsx`
  - 摘要文案改为 `Tabs: {slots} / panes: {windows}`，避免 `1 tabs / 1 panes`。
- `apps/web/src/components/ConfigEditor.test.tsx`
  - 覆盖 3 个 tmux windows 仍显示为 1 个 pane。

### 8. Dashboard 计数文案仍有 `1 tabs / 1 panes`

问题：

- Dashboard 的标签页摘要直接使用 `{total} tabs · {windows} panes`。
- 当 `research-projects` 这类单标签、单外部 pane 的工作空间打开时，会显示 `1 tabs · 1 panes`。

影响：

- 这是很小但很可见的精致度问题。
- 用户会感到 UI 仍像内部调试面板，没有经过最终产品打磨。

修复：

- `apps/web/src/components/dashboard-view-model.ts`
  - 新增 `workspaceCountLabel()`，把 Dashboard 计数格式从组件中抽到 view model。
- `apps/web/src/i18n/index.tsx`
  - 新增英文单复数 key：`tabCountOne`、`workspacePaneCountOne`、`workspacePaneCount`。
  - 中文仍保持 `{count} 个标签页 / {count} 个窗格`。
- `apps/web/src/components/Dashboard.tsx`
  - Dashboard 摘要改用 `workspaceCountLabel()`。
- `apps/web/src/components/dashboard-view-model.test.ts` 和 `Dashboard.test.tsx`
  - 覆盖 `1 tab · 1 pane`，防止回退成 `1 tabs · 1 panes`。

验证：

- 浏览器截图：
  - `tmp/review-live-2026-05-14/research-dashboard-counts-fixed.png`
- 断言：
  - 页面包含 `1 tab · 1 pane`。
  - 页面不包含 `1 tabs · 1 panes`。

### 9. Project config 默认启动工具会保存旧 opener id

问题：

- Project config 的默认启动工具下拉框仍使用旧值 `terminal` / `iterm`。
- 后端 opener 注册表实际使用 `terminal-app` / `iterm2`。
- YAML parser 也没有把旧 id 归一化到注册表 id。

影响：

- 用户在项目配置里选择默认启动工具后，可能保存出后端无法识别的 `openWith`。
- 后续点击 Dashboard 的启动动作时，会出现“配置看起来能保存，但启动器不能正确 dispatch”的隐性故障。

修复：

- `apps/web/src/components/ConfigEditor/ProjectSection.tsx`
  - 下拉选项改为注册表 id：`terminal-app`、`iterm2`。
- `apps/web/src/components/ConfigEditor/yaml-utils.ts`
  - 新增 opener id 归一化，兼容读取旧配置里的 `terminal` / `iterm`。
- `cc_branch/models/config.py`
  - 后端加载配置时同样归一化旧 opener id，避免旧 YAML 继续污染运行路径。
- `apps/web/src/components/ConfigEditor.test.tsx`
  - 覆盖 UI 保存 `Terminal.app` 时写出 `openWith: terminal-app`。
- `apps/web/src/components/ConfigEditor/yaml-utils.test.ts`
  - 覆盖旧 id parse 后变成注册表 id。
- `tests/test_config.py`
  - 覆盖后端加载旧 `openWith` 后归一化。

验证：

- `cd apps/web && npm test -- ConfigEditor.test.tsx yaml-utils.test.ts`
- `python3.11 -m unittest tests.test_config.ConfigTests.test_load_workspace_normalizes_legacy_open_with_ids tests.test_config.ConfigTests.test_load_workspace_parses_canonical_workspace_terms tests.test_config.ConfigTests.test_workspace_to_dict_serializes_canonical_terms`
- `cd apps/web && npm test && npm run lint && npm run build`
- `python3.11 -m unittest discover tests`
- `python scripts/build-webui.py`
- 浏览器截图：
  - `tmp/review-live-2026-05-14/project-opener-selector-fixed.png`

### 10. Layout opener 把 tmux 内部窗口误展开成外部窗格

问题：

- 当前概念里，Tmux group 在外部 terminal/editor 里应该只占一个 Pane。
- 但打开整个 workspace 时，`WorkspaceOpenActions` 仍使用 `tmux_window_attach_specs()`。
- Warp / VS Code / Cursor 这类 layout 或 workspace-file opener 会收到每个 tmux window 一条命令：
  - `cc-branch attach dev:planner`
  - `cc-branch attach dev:review`
- 这会把 tmux 内部窗口展开成多个外部 terminal pane。

影响：

- 用户在空间画布里看到的是 “1 个 tmux 窗格组”，实际打开却变成多个外部窗格。
- Warp 自动布局会出现不必要的 1/2、1/4、1/8 分割，越开越碎。
- VS Code / Cursor 的任务 fallback 也会生成多个外部 terminal，而不是一个承载 tmux session 的 terminal。

修复：

- `cc_branch/application/workspace_actions/open.py`
  - workspace 级 layout opener / workspace-file opener 改用 `tmux_slot_attach_specs()`。
  - 打开整个工作空间时生成 `cc-branch attach dev`，让 tmux 内部管理 windows。
- `cc_branch/application/workspace_actions/command_specs.py`
  - slot 级 attach target 也改为 `cc-branch attach <tab>`。
  - window 级 target 仍保留 `cc-branch attach <tab>:<window>`。
- `tests/test_webui.py` 和 `tests/test_application_architecture.py`
  - 更新并覆盖 Warp / VS Code / mixed workspace 的新语义。

验证：

- `python3.11 -m unittest tests.test_webui.WebUIHandlerTests.test_action_open_workspace_with_layout_opener_opens_all_slots tests.test_webui.WebUIHandlerTests.test_action_open_workspace_with_vscode_opens_workspace_file tests.test_webui.WebUIHandlerTests.test_action_open_mixed_workspace_with_vscode_opens_workspace_file tests.test_webui.WebUIHandlerTests.test_action_open_workspace_with_vscode_generates_tasks tests.test_webui.WebUIHandlerTests.test_action_open_workspace_with_warp_keeps_tmux_slot_as_one_layout_pane tests.test_webui.WebUIHandlerTests.test_action_open_slot_with_vscode_opens_workspace_file tests.test_webui.WebUIHandlerTests.test_action_open_target_with_vscode_opens_workspace_file tests.test_application_architecture.WorkspaceActionsTests.test_open_workspace_layout_opener_keeps_tmux_slot_as_one_external_pane`
- `python3.11 -m unittest tests.test_webui tests.test_application_architecture`

## 仍需后续处理的风险

### 1. 配置概念仍然复杂

当前概念已经趋于清晰：

- Tab：外部 terminal/editor 里的标签页容器。
- Pane：Tab 内的可视终端区域。
- Tmux group：一个 Pane 内由 tmux 管理的一组 windows。
- Tmux window：tmux group 内部可切换的窗口。

但 UI 里仍然需要持续压低解释性文字，让画布本身承担更多所见即所得表达。

### 2. Doctor 仍需继续从检查页升级为产品诊断

Doctor 现在能合并配置问题和 runtime drift，也已经把通过项降级到详情区，主列表优先展示真正需要处理的错误和警告。下一步应该继续把它收敛为“这个工作空间为什么启动不了 / 为什么状态不一致 / 下一步做什么”的产品级诊断，而不只是 CLI 工具可用性检查。

补充修复：全通过状态已经进一步压缩，首屏不再重复展示 `All checks passed` / `Workspace checks are clear` / `Ready to launch`，只保留顶部结论和可展开的 passed checks。

### 3. 本轮只做了局部 UI 修复

Dashboard 主动作区已经修过，但 Space canvas / Project config 的整体视觉统一还没有达到“最终完成”。下一步更应该集中在：

- 复杂布局下的拖拽预览、失败态和落点方向提示。
- tmux group 的信息层级。
- Project config 中全局配置和工作空间配置的区分。

架构上，`SlotsSection.tsx` 已继续把 inspector 的调度派生逻辑抽成 `workspace-inspector-model.ts`。后续剩余重点是表单 patch 与 action wiring，而不是继续让组件承载业务规则。

## 验证记录

已通过：

```bash
python3.11 -m unittest tests.test_application_architecture tests.test_config -q
cd apps/web && npm test -- ConfigEditor.test.tsx DoctorView.test.tsx
cd apps/web && npm run lint
cd apps/web && npm run build
python3.11 -m ruff check cc_branch tests
python3.11 scripts/build-webui.py
```

全量验证也已通过：

```bash
python3.11 -m unittest discover tests
cd apps/web && npm test
```

类型检查也已补跑并纳入 CI：

```bash
uv run --with mypy --with types-PyYAML mypy cc_branch
python3.11 -m mypy --platform linux cc_branch
python3.11 -m mypy --platform win32 cc_branch
```

结果：

```text
Success: no issues found in 150 source files
```

当前后端接口验证：

```bash
curl -sS 'http://127.0.0.1:5194/api/config?project_path=/Users/geminilight/code/cli-workspace'
```

结果中的 `issues` 为 `[]`。

# CC Branch 目标完成度审计

日期：2026-05-14
范围：本轮围绕代码架构、功能缺陷、UI/UX 精修的连续审查与修复。

## 目标拆解

原始目标可以拆成三个交付标准：

1. 架构审查：整体软件架构更专业、更高质量、更可维护。
2. 功能审查：发现潜在功能 bug，并把确认的问题修好。
3. UI/UX 优化：继续打磨用户体验，让产品更精致、更愿意被使用。

## 证据清单

| 要求 | 产物 / 证据 | 当前结论 |
| --- | --- | --- |
| 审查配置模型和运行时 adapter 一致性 | `cc_branch/application/config_validation/constants.py`、`tests/test_application_architecture.py` | 已修复：`internal` 枚举与 runtime adapter 对齐，`command` 不再被误接受。 |
| 审查配置 v2 公共字段 | `apps/web/src/utils/configIssues.ts`、`configIssues.test.ts`、`ConfigEditor`、`DoctorView` | 已修复：`openWith` / `layoutBackend` 不再通过旧缓存路径误报 unknown field；过滤逻辑现在会检查 target，避免隐藏 agent/window 等非法位置里的真实 unknown-field 问题。 |
| 审查 YAML round-trip 风险 | `apps/web/src/components/ConfigEditor/yaml-utils.test.ts` | 已补保护：普通 pane + tmux group 混合 tab 可以 parse / serialize / reparse。 |
| 审查 Dashboard 主动作区 | `apps/web/src/components/Dashboard.tsx`、截图 `tmp/review-pass/*` | 已局部修复：工具选择、打开目录、刷新、启动按钮不再明显截断或换行。 |
| 优化 Dashboard runtime 状态解释 | `apps/web/src/components/Dashboard.tsx`、`Dashboard.test.tsx` | 已修复：runtime changed / untracked / extra 等状态不再只藏在 `sr-only` 中；用户能在标签页区域直接看到紧凑的可见原因提示。 |
| 修复 Dashboard runtime 计数一致性 | `apps/web/src/components/dashboard-view-model.ts`、`dashboard-view-model.test.ts`、`Dashboard.tsx` | 已修复：当 runtime drift 只出现在 `runtime_sync.summary` 而 pane/slot 上没有同步状态时，仪表盘不再显示“0 runtime update(s)”同时又展示 warning；计数现在取 pane-level drift 与 summary changed/untracked 的较大值，并加上 extra / tmux unavailable。 |
| 审查 Project config 术语 | `apps/web/src/i18n/index.tsx` | 已修复：不再把 `Layout backend` 这种工程词直接暴露给用户。 |
| 优化 Project config 信息架构 | `apps/web/src/components/ConfigEditor/ProjectSection.tsx`、`apps/web/src/i18n/index.tsx`、`ConfigEditor.test.tsx` | 已推进：项目配置页拆成 Workspace identity 和 Launch defaults 两组，默认启动工具、默认窗格类型和默认 Shell 不再藏在 `Advanced defaults` 原生折叠区里。 |
| 降低 Project config 首屏负担 | `apps/web/src/components/ConfigEditor/index.tsx`、`ConfigEditor.test.tsx`、截图 `tmp/review-live-2026-05-14/project-agent-collapsed.png` | 已优化：低频的 Agent overrides 默认收起，只保留摘要和 Add 入口，避免进入项目配置时先看到一长串高级 agent 覆盖项。 |
| 收敛新建配置向导模型 | `apps/web/src/components/config-wizard-model.ts`、`config-wizard-model.test.ts`、`ConfigWizard.tsx` | 已推进：模板规格、agent 选择、统计、YAML 生成从 React 组件抽成纯模型；向导 YAML 现在复用主配置编辑器 serializer，不再手工拼字符串，特殊字符会由 `js-yaml` 正确转义。 |
| 修复项目级 Agent 覆盖默认模板 | `apps/web/src/components/ConfigEditor/AgentsSection.tsx`、`AgentsSection.test.tsx` | 已修复：新增自定义 agent 时默认 `create_template` 使用官方 `{session_id}` 模板语法，不再生成 `{{session_id}}`。 |
| 防止双花括号模板生成坏命令 | `cc_branch/templates.py`、`tests/test_templates.py`、`tests/test_cli.py` | 已修复：模板渲染现在优先处理 `{{session_id}}`，再处理 `{session_id}`；CLI resume 场景确认不会再输出 `claude resume {uuid}` 或残留 `{session_id}`。 |
| 审查 tmux group 计数 | `ConfigEditor/index.tsx`、`SlotsSection.tsx`、`ConfigEditor.test.tsx` | 已修复：tmux group 在外部空间按 1 个 pane 计数，内部 tmux windows 不误算。 |
| 收敛 workspace 术语模型 | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts` | 已继续推进：tmux group / legacy tmux slot / pane count / canvas pane 投影 / fallback terminal pane / selection clamp 等纯逻辑已从组件中抽出并加测试。 |
| 审查跨标签页拖拽语义 | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`SlotsSection.tsx`、`workspace-model.test.ts` | 已修复：Tab 作为容器不再限制 pane/tmux group 移动；legacy tmux tab 拖入其它 tab 时会转换为目标 tab 中的 tmux group。 |
| 修复隐式 terminal pane 跨标签拖拽 | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts`、`ConfigEditor.test.tsx` | 已修复：没有显式 `panes/windows` 的 terminal 标签页也能作为一个真实窗格拖入其它标签页，移动后源标签页会被移除。 |
| 对齐隐式 terminal pane 的画布与详情 | `apps/web/src/components/ConfigEditor/WorkspaceDetailEditors.tsx`、`ConfigEditor.test.tsx` | 已修复：没有显式 `panes/windows` 的 terminal 标签页在画布中显示为隐式窗格时，右侧详情标题不再为空，而是回落到同一个标签页/窗格名；直接改名会同步更新画布。 |
| 对齐隐式 terminal pane 的详情调度能力 | `apps/web/src/components/ConfigEditor/SlotsSection.tsx`、`ConfigEditor.test.tsx` | 已修复：隐式 terminal pane 不再只能通过画布拖拽跨标签移动；右侧详情里的“移动到标签页”现在也会出现，并能把源标签页正确移除。 |
| 覆盖画布拖拽保存持久化 | `scripts/qa/verify-workspace-drag.py`、`tests/fixtures/browser-drag-project/.cc-branch/config.yaml` | 已补浏览器级保存验证：拖拽 terminal pane 和 tmux group 后点击 Save，再读取 YAML，确认目标 tab、pane 顺序、`zsh` 命令和 tmux nested windows 都被保存。 |
| 避免 Web UI 动态数据陈旧 | `cc_branch/webui/server/handler.py`、`tests/test_webui.py` | 已修复：所有 API JSON 响应增加 `Cache-Control: no-store`，避免配置、诊断、状态被浏览器缓存成旧结果。 |
| 审查 Doctor 整体健康态 | `apps/web/src/components/DoctorView.tsx`、`DoctorView.test.tsx` | 已修复：配置问题、运行时漂移、缺失的 tmux 托管窗格和结构化 doctor issues 会共同决定顶部健康态，不再出现下方有错误但顶部显示全部通过。 |
| 优化 Doctor 阅读顺序和产品语义 | `apps/web/src/components/DoctorView.tsx`、`apps/web/src/i18n/index.tsx`、`DoctorView.test.tsx` | 已推进：标题从 Health Check 收敛为 Workspace diagnosis，详细列表改为问题/警告优先，避免用户先读到通过项再看到待处理问题。 |
| 拆分 Doctor view model | `apps/web/src/components/doctor-view-model.ts`、`doctor-view-model.test.ts`、`DoctorView.tsx` | 已推进：文本 report 解析、结构化 issue 映射、配置 issue 过滤、runtime drift 汇总、整体健康态和计数文案从 React 组件抽成纯 view model，并补单元测试。 |
| 降低 Doctor 空状态视觉噪音 | `apps/web/src/components/DoctorView.tsx` | 已优化：摘要卡片只有在对应数量大于 0 时使用错误/警告/通过强调色；0 项状态用中性图标和弱背景，减少误导。 |
| 清理 Doctor 通过项提示噪音 | `apps/web/src/components/doctor-view-model.ts`、`doctor-view-model.test.ts`、截图 `tmp/review-pass/doctor-view-2026-05-14-after.png` | 已修复：结构化 info 级 doctor issue 和文本 report 的通过项即使携带 hint，也不再显示“修复提示”。 |
| 降低 Doctor 主列表噪音 | `apps/web/src/components/DoctorView.tsx`、`doctor-view-model.ts`、`DoctorView.test.tsx`、`doctor-view-model.test.ts`、截图 `tmp/review-live-2026-05-14/doctor-actionable-first.png` | 已优化：诊断页主列表默认只展示需要处理的错误/警告；通过项折到低权重详情区；全通过状态不再显示 `0 issues / 0 warnings`。 |
| 审查 agent 图标显示一致性 | `apps/web/src/components/ui/AgentMark.tsx`、`Dashboard.tsx`、`SlotsSection.tsx` | 已收敛：Dashboard 和配置画布不再各自复制 Codex / Claude / Gemini / Cursor / Kimi 的识别与 icon 样式。 |
| 拆分 workspace canvas 渲染职责 | `apps/web/src/components/ConfigEditor/WorkspaceCanvas.tsx`、`workspace-display.ts`、`SlotsSection.tsx` | 已推进：画布 JSX、pane 样式投影和展示摘要从 `SlotsSection.tsx` 拆出，`SlotsSection.tsx` 从 1666 行降到 1352 行。 |
| 拆分 session 选择器职责 | `apps/web/src/components/ConfigEditor/SessionInput.tsx`、`SlotsSection.tsx` | 已推进：agent session 加载、resume/fresh/auto 状态和下拉选择逻辑从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 1205 行。 |
| 拆分布局选择控件 | `apps/web/src/components/ConfigEditor/LayoutPicker.tsx`、`SlotsSection.tsx` | 已推进：tab layout glyph 和 segmented picker 从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 1097 行。 |
| 拆分 inspector 动作区 | `apps/web/src/components/ConfigEditor/InspectorActions.tsx`、`SlotsSection.tsx` | 已推进：pane 调度、移动到标签页、删除 pane、tmux group 位置操作从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 988 行。 |
| 拆分 tmux group 编辑器 | `apps/web/src/components/ConfigEditor/TmuxGroupEditor.tsx`、`SlotsSection.tsx` | 已推进：tmux group 名称、内部 tmux window 列表、agent/session/advanced/env 编辑从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 843 行。 |
| 拆分标签页和普通窗格编辑器 | `apps/web/src/components/ConfigEditor/WorkspaceDetailEditors.tsx`、`SlotsSection.tsx` | 已推进：tab 编辑、terminal pane 编辑、agent pane 编辑从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 672 行。 |
| 拆分画布拖拽协调逻辑 | `apps/web/src/components/ConfigEditor/workspace-drag.ts`、`WorkspaceCanvas.tsx`、`SlotsSection.tsx` | 已推进：HTML5 drag payload、drop midpoint、append drop 和 drag state 从 workspace 编辑器中抽成 hook，`SlotsSection.tsx` 进一步降到 587 行。 |
| 补拖拽落点判断测试 | `apps/web/src/components/ConfigEditor/workspace-drag.test.ts` | 已补保护：横向、纵向、main-top/main-left/grid/auto 布局下的 drop midpoint 判断有纯函数测试覆盖。 |
| 补画布内 pane 拖拽集成测试 | `apps/web/src/components/ConfigEditor.test.tsx` | 已补保护：同一 tab 内 terminal pane 可以通过 workspace matrix 拖拽重排，覆盖用户最常见的画布内调度路径。 |
| 补真实浏览器拖拽验证 | `scripts/qa/verify-workspace-drag.py`、`tests/fixtures/browser-drag-project/.cc-branch/config.yaml` | 已验证：本地 `cc-branch serve` + Chromium Playwright 中，terminal pane 和 legacy tmux tab / tmux group 都可以真实拖入另一个标签页；源标签页被移除，目标标签页保留所有窗格。 |
| 强化画布选中态和拖拽反馈 | `apps/web/src/components/ConfigEditor/WorkspaceCanvas.tsx`、`ConfigEditor.test.tsx`、截图 `tmp/review-live-2026-05-14/workspace-canvas-feedback.png` | 已优化：选中 tab/pane 有更明确的 ring；拖拽源和候选落点有可见状态，并有测试覆盖 `data-drag-source` / `data-drop-candidate` 状态。 |
| 拆分 selection 派生状态 | `apps/web/src/components/ConfigEditor/workspace-selection.ts`、`workspace-selection.test.ts`、`SlotsSection.tsx` | 已推进：空工作区、空 terminal tab、普通 terminal pane、legacy tmux tab、显式 tmux group 的选中态判断从组件中抽出并加测试，`SlotsSection.tsx` 进一步降到 580 行。 |
| 拆分标签页新增/删除 mutation | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts`、`SlotsSection.tsx` | 已推进：新增标签页的唯一命名、默认 terminal/tmux 初始化和删除后的选中态从组件中抽成纯 mutation，并补单元测试，`SlotsSection.tsx` 进一步降到 559 行。 |
| 拆分同标签页窗格移动 mutation | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts`、`SlotsSection.tsx` | 已推进：同一 tab 内按方向移动 pane 的边界判断、排序和选中态从组件中抽成纯 mutation，并补单元测试，`SlotsSection.tsx` 进一步降到 553 行。 |
| 拆分窗格新增/复制/删除 mutation | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts`、`SlotsSection.tsx` | 已推进：pane add / duplicate / delete 的 legacy tmux 转换、隐式 terminal tab 复制/删除、显式 pane 插入/删除和无效索引保护已抽成纯 mutation，并补单元测试，`SlotsSection.tsx` 进一步降到 504 行。 |
| 拆分 tmux 内部 window mutation | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts`、`SlotsSection.tsx` | 已推进：legacy tmux tab 和显式 tmux group 内部 window 的 add / update / move / delete 已抽成纯 mutation，并补单元测试，`SlotsSection.tsx` 进一步降到 483 行。 |
| 加固 pane 移动 mutation 的异常索引处理 | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts` | 已修复：同标签页移动、跨标签页移动、legacy tmux group 移动都会拒绝负数和越界 source pane index，避免异常拖拽 payload 触发 `splice(-1)` 误移动最后一个窗格。 |
| 避免 UI 自动生成重复名称 | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts` | 已修复：新增/复制 tab、pane、tmux window 时会基于 trim 后名称生成唯一名称，避免 UI 自己制造随后被校验挡住的重复名。 |
| 拆分工作空间名称校验 | `apps/web/src/components/ConfigEditor/workspace-validation.ts`、`workspace-validation.test.ts`、`SlotsSection.tsx`、`yaml-utils.ts` | 已推进：标签页/窗格空名称和重复标签页名称校验从组件中抽成纯函数，并复用于保存前 `validateConfigForm`；重复名会先 trim，避免 `dev` 和 ` dev ` 逃过校验，`SlotsSection.tsx` 进一步降到 478 行。 |
| 对齐后端名称重复校验 | `cc_branch/application/config_validation/validators.py`、`cc_branch/doctor/checks.py`、`tests/test_application_architecture.py`、`tests/test_doctor.py` | 已修复：raw config validation 和 doctor 现在也会先 trim 名称再判断重复，避免 UI 保存前校验和后端诊断结果不一致。 |
| 审查中英文文案一致性 | `apps/web/src/i18n/index.tsx` | 已修复：tmux windows / tmux group 文案不再中英文混杂。 |
| 审查本地生成物污染提交视图 | `.gitignore` | 已修复：忽略 `.cc-branch/.generated/` 和 `tmp/`。 |
| 审查结果可追踪 | `docs/review/current-product-review-2026-05-14.md` | 已落文档：记录本轮发现、修复、验证和剩余风险。 |

## 验证记录

已在当前状态通过：

```bash
python3.11 -m unittest tests.test_templates tests.test_cli.CLITests.test_session_command_accepts_colon_target tests.test_cli.CLITests.test_session_command_renders_double_brace_session_templates
```

结果：

```text
Ran 4 tests in 0.018s
OK
```

```bash
python3.11 -m unittest discover tests
```

结果：

```text
Ran 391 tests in 48.855s
OK
```

```bash
python3.11 -m unittest tests.test_application_architecture.ConfigWorkflowTests.test_collect_config_issues_normalizes_names_before_duplicate_checks tests.test_doctor.DoctorTests.test_doctor_normalizes_names_before_duplicate_checks
```

结果：

```text
Ran 2 tests in 0.012s
OK
```

```bash
cd apps/web && npm test
```

结果：

```text
Test Files  27 passed (27)
Tests  198 passed (198)
```

```bash
cd apps/web && npm run lint && npm run build
```

结果：ESLint 通过，Vite production build 通过。

```bash
cd apps/web && npm test -- DoctorView.test.tsx doctor-view-model.test.ts
```

结果：

```text
Test Files  2 passed (2)
Tests  12 passed (12)
```

```bash
/Users/geminilight/opt/anaconda3/bin/python - <<'PY'
# Playwright smoke: open Doctor tab and assert passing checks do not show "Check your configuration" remediation hints.
PY
```

结果：

```text
screenshot tmp/review-pass/doctor-view-2026-05-14-after.png
```

```bash
cd apps/web && npm test -- DoctorView.test.tsx
```

结果：

```text
Test Files  1 passed (1)
Tests  5 passed (5)
```

```bash
cd apps/web && npm test -- yaml-utils.test.ts workspace-validation.test.ts ConfigEditor.test.tsx
```

结果：

```text
Test Files  3 passed (3)
Tests  32 passed (32)
```

```bash
/Users/geminilight/opt/anaconda3/bin/python - <<'PY'
# Playwright smoke: open Project config and verify Workspace identity / Launch defaults are visible.
PY
```

结果：

```text
screenshot tmp/review-pass/project-config-2026-05-14.png
Workspace identity visible; Launch defaults visible; Advanced defaults absent.
```

```bash
python scripts/build-webui.py
./bin/cc-branch --project /Users/geminilight/code/cli-workspace/tmp/browser-save-project serve --port 5198
python scripts/qa/verify-workspace-drag.py http://127.0.0.1:5198 tmp/browser-qa/workspace-drag-save-after.png tmp/browser-save-project/.cc-branch/config.yaml
```

结果：

```text
PASS: browser drag moved terminal pane and tmux group into another tab
PASS: saved YAML persisted the moved terminal pane and tmux group
pane labels: ['Edit pane shell', 'Edit pane review', 'Edit pane ui', 'Edit pane spec']
tab labels: ['Edit tab dev']
```

```bash
python3.11 -m ruff check cc_branch tests
```

结果：

```text
All checks passed!
```

当前后端配置接口：

```bash
curl -sS 'http://127.0.0.1:5194/api/config?project_path=/Users/geminilight/code/cli-workspace'
```

结果中的 `issues` 为：

```text
[]
```

Git 状态：

```text
main...origin/main
```

最近提交：

```text
bd9063d Prevent stale Web UI API caching
d1273b0 Verify workspace drag save persistence
3949149 Cover tmux group browser drag QA
```

## 未完全覆盖的要求

### 1. “整体架构更专业、更高质量、更可维护”尚未完全证明

已修复的点集中在配置校验、前端展示一致性、局部工具链卫生。它们提高了维护性，但还没有完成一次完整的架构重构或架构边界审计。

剩余不确定性：

- 配置模型仍存在 `slots/windows` 存储术语与 `tabs/panes/tmux groups` 产品术语的映射层。
- 前端 `SlotsSection.tsx` 已抽出更多纯模型逻辑、跨 tab 移动逻辑、agent icon 显示逻辑、canvas rendering、session 选择器、layout picker、inspector 动作区、tmux group 编辑器、tab/terminal pane/agent pane 编辑器、drag/drop coordination、selection 派生状态、tab mutation、主要 pane mutation 和 tmux internal window mutation，但仍然承担少量选择态、表单 patch 和 action wiring。
- Doctor 已开始从“检查日志列表”收敛为 workspace health diagnosis：主列表优先展示 actionable findings，通过项默认折叠；但更深层的修复操作编排、启动阻塞原因归因仍未完全产品化。

### 2. “任何潜在功能 bug”无法用当前证据宣称全部发现

已修复多个实际 bug，但“任何潜在 bug”是开放集合。当前证据只能证明：

- 已覆盖已发现的配置枚举、旧 warning、YAML round-trip、pane count 等问题。
- 全量现有自动测试通过。

不能证明：

- 所有 opener 在所有系统上都无问题。
- VS Code / Cursor / Warp 的所有布局启动路径都在当前审计中重新端到端验证。
- 拖拽交互已有模型层覆盖跨 tab 移动、legacy tmux group 转换、隐式 terminal pane 跨 tab 移动、最后一个 pane 移动后删除空 tab，并补了 jsdom 集成层的同 tab pane 重排验证和隐式 terminal pane 跨 tab 拖拽验证；真实浏览器中已验证 terminal pane 和 legacy tmux tab / tmux group 跨 tab 拖拽，以及拖拽后的 YAML 保存持久化。

### 3. “非常非常完美”的 UI/UX 尚未达到可关闭标准

本轮 UI/UX 从明显错误状态推进到更一致，但仍有可见风险：

- Space canvas 还可以继续降低配置编辑器感，更像真实 workspace 预览。
- 选中态和拖拽候选落点已有更明确的 ring/outline 反馈；但复杂布局下的拖拽预览、失败态和落点方向提示还可以更精细。
- Project config 仍需要继续区分“项目级信息”和“工作空间布局信息”。
- Doctor 已降低通过项噪音，但还需要更贴近用户问题，例如把“为什么启动不了 / 应该先处理哪个配置或运行态差异”继续做成更直接的产品诊断。

## 审计结论

当前目标 **尚未完成**。

理由：

- 本轮已经完成多项有证据的架构一致性、功能 bug、UI/UX 修复。
- 自动测试和构建状态可靠。
- 但原始目标的范围包含“整体架构设计全面审查”和“UI/UX 非常精致”，当前仍有未覆盖和未充分验证的部分。

下一步最值得继续的方向：

1. 继续拆分 `SlotsSection.tsx` 的职责；本轮已抽出更多 workspace model、pane movement、canvas rendering、session selector、layout picker、inspector actions、tmux group editor、detail editors、drag/drop coordination、selection derivation、tab add/delete mutations、主要 pane mutations 和 tmux internal window mutations，下一步应继续收敛表单 patch/action wiring。
2. 继续扩大 workspace canvas 浏览器级交互验证，重点覆盖拖拽态视觉反馈、失败态和更多布局组合。
3. 继续重构 Doctor 的信息架构，把 actionable diagnosis 和可执行修复路径做得更像 workspace health，而不是环境检查报告。

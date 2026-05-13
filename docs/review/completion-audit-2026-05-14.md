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
| 审查配置 v2 公共字段 | `apps/web/src/utils/configIssues.ts`、`ConfigEditor`、`DoctorView` | 已修复：`openWith` / `layoutBackend` 不再通过旧缓存路径误报 unknown field。 |
| 审查 YAML round-trip 风险 | `apps/web/src/components/ConfigEditor/yaml-utils.test.ts` | 已补保护：普通 pane + tmux group 混合 tab 可以 parse / serialize / reparse。 |
| 审查 Dashboard 主动作区 | `apps/web/src/components/Dashboard.tsx`、截图 `tmp/review-pass/*` | 已局部修复：工具选择、打开目录、刷新、启动按钮不再明显截断或换行。 |
| 审查 Project config 术语 | `apps/web/src/i18n/index.tsx` | 已修复：不再把 `Layout backend` 这种工程词直接暴露给用户。 |
| 审查 tmux group 计数 | `ConfigEditor/index.tsx`、`SlotsSection.tsx`、`ConfigEditor.test.tsx` | 已修复：tmux group 在外部空间按 1 个 pane 计数，内部 tmux windows 不误算。 |
| 收敛 workspace 术语模型 | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`workspace-model.test.ts` | 已继续推进：tmux group / legacy tmux slot / pane count / canvas pane 投影 / fallback terminal pane / selection clamp 等纯逻辑已从组件中抽出并加测试。 |
| 审查跨标签页拖拽语义 | `apps/web/src/components/ConfigEditor/workspace-model.ts`、`SlotsSection.tsx`、`workspace-model.test.ts` | 已修复：Tab 作为容器不再限制 pane/tmux group 移动；legacy tmux tab 拖入其它 tab 时会转换为目标 tab 中的 tmux group。 |
| 审查 agent 图标显示一致性 | `apps/web/src/components/ui/AgentMark.tsx`、`Dashboard.tsx`、`SlotsSection.tsx` | 已收敛：Dashboard 和配置画布不再各自复制 Codex / Claude / Gemini / Cursor / Kimi 的识别与 icon 样式。 |
| 拆分 workspace canvas 渲染职责 | `apps/web/src/components/ConfigEditor/WorkspaceCanvas.tsx`、`workspace-display.ts`、`SlotsSection.tsx` | 已推进：画布 JSX、pane 样式投影和展示摘要从 `SlotsSection.tsx` 拆出，`SlotsSection.tsx` 从 1666 行降到 1352 行。 |
| 拆分 session 选择器职责 | `apps/web/src/components/ConfigEditor/SessionInput.tsx`、`SlotsSection.tsx` | 已推进：agent session 加载、resume/fresh/auto 状态和下拉选择逻辑从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 1205 行。 |
| 拆分布局选择控件 | `apps/web/src/components/ConfigEditor/LayoutPicker.tsx`、`SlotsSection.tsx` | 已推进：tab layout glyph 和 segmented picker 从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 1097 行。 |
| 拆分 inspector 动作区 | `apps/web/src/components/ConfigEditor/InspectorActions.tsx`、`SlotsSection.tsx` | 已推进：pane 调度、移动到标签页、删除 pane、tmux group 位置操作从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 988 行。 |
| 拆分 tmux group 编辑器 | `apps/web/src/components/ConfigEditor/TmuxGroupEditor.tsx`、`SlotsSection.tsx` | 已推进：tmux group 名称、内部 tmux window 列表、agent/session/advanced/env 编辑从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 843 行。 |
| 拆分标签页和普通窗格编辑器 | `apps/web/src/components/ConfigEditor/WorkspaceDetailEditors.tsx`、`SlotsSection.tsx` | 已推进：tab 编辑、terminal pane 编辑、agent pane 编辑从 workspace 编辑器中抽出，`SlotsSection.tsx` 进一步降到 672 行。 |
| 审查中英文文案一致性 | `apps/web/src/i18n/index.tsx` | 已修复：tmux windows / tmux group 文案不再中英文混杂。 |
| 审查本地生成物污染提交视图 | `.gitignore` | 已修复：忽略 `.cc-branch/.generated/` 和 `tmp/`。 |
| 审查结果可追踪 | `docs/review/current-product-review-2026-05-14.md` | 已落文档：记录本轮发现、修复、验证和剩余风险。 |

## 验证记录

已在当前状态通过：

```bash
python3.11 -m unittest discover tests
```

结果：

```text
Ran 384 tests in 50.237s
OK
```

```bash
cd apps/web && npm test
```

结果：

```text
Test Files  19 passed (19)
Tests  131 passed (131)
```

```bash
cd apps/web && npm run lint && npm run build
```

结果：ESLint 通过，Vite production build 通过。

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
ce37e5b Ignore local generated review artifacts
4107b61 Fix workspace canvas pane counts
8e47fd0 Polish config validation and workspace UI
```

## 未完全覆盖的要求

### 1. “整体架构更专业、更高质量、更可维护”尚未完全证明

已修复的点集中在配置校验、前端展示一致性、局部工具链卫生。它们提高了维护性，但还没有完成一次完整的架构重构或架构边界审计。

剩余不确定性：

- 配置模型仍存在 `slots/windows` 存储术语与 `tabs/panes/tmux groups` 产品术语的映射层。
- 前端 `SlotsSection.tsx` 已抽出更多纯模型逻辑、跨 tab 移动逻辑、agent icon 显示逻辑、canvas rendering、session 选择器、layout picker、inspector 动作区、tmux group 编辑器、tab/terminal pane/agent pane 编辑器，但仍然承担拖拽事件和整体 selection 编排。
- Doctor 仍偏 CLI 环境检查，尚未完全产品化为 workspace health diagnosis。

### 2. “任何潜在功能 bug”无法用当前证据宣称全部发现

已修复多个实际 bug，但“任何潜在 bug”是开放集合。当前证据只能证明：

- 已覆盖已发现的配置枚举、旧 warning、YAML round-trip、pane count 等问题。
- 全量现有自动测试通过。

不能证明：

- 所有 opener 在所有系统上都无问题。
- VS Code / Cursor / Warp 的所有布局启动路径都在当前审计中重新端到端验证。
- 拖拽交互已有模型层覆盖跨 tab 移动、legacy tmux group 转换、最后一个 pane 移动后删除空 tab，但仍缺少真实浏览器级拖拽验证。

### 3. “非常非常完美”的 UI/UX 尚未达到可关闭标准

本轮 UI/UX 从明显错误状态推进到更一致，但仍有可见风险：

- Space canvas 还可以继续降低配置编辑器感，更像真实 workspace 预览。
- 选中态、拖拽态、跨 tab 移动的反馈还可以更精细。
- Project config 仍需要继续区分“项目级信息”和“工作空间布局信息”。
- Doctor 需要更贴近用户问题，而不是只列环境检查。

## 审计结论

当前目标 **尚未完成**。

理由：

- 本轮已经完成多项有证据的架构一致性、功能 bug、UI/UX 修复。
- 自动测试和构建状态可靠。
- 但原始目标的范围包含“整体架构设计全面审查”和“UI/UX 非常精致”，当前仍有未覆盖和未充分验证的部分。

下一步最值得继续的方向：

1. 继续拆分 `SlotsSection.tsx` 的职责；本轮已抽出更多 workspace model、pane movement、canvas rendering、session selector、layout picker、inspector actions、tmux group editor 和 detail editors，下一步应拆 drag/drop coordination。
2. 为 workspace canvas 增加端到端交互测试，覆盖真实浏览器拖拽、tmux group 移动、复杂布局保存。
3. 重构 Doctor 的信息架构，让它从环境检查升级为 workspace health diagnosis。

# CC Branch 当前代码与产品审查增量

日期：2026-05-15
范围：在 2026-05-14 审查基础上，继续检查 Web UI 配置操作、全局 Agent 覆盖保存、项目/配置状态流和前端验证链路。

## 当前结论

本轮继续推进了三个方向：

- 架构质量：全局 Agent 配置从“保存完整有效态”收敛为“只保存用户覆盖”，减少内置定义和用户配置互相污染。
- 功能正确性：修复配置方案操作目标漂移风险，避免确认删除、复制、重命名时读取到刷新后的错误选中项。
- UI/UX 质量：把内置 Agent 名称锁定为稳定标识，避免用户误以为可以重命名内置 Agent；配置方案操作仍保持 inline 轻量编辑，不引入额外阻塞流程。

这些修复都已提交到 `main`，并通过 GitHub Actions。

## 已确认并修复的问题

### 1. 全局 Agent 覆盖会把内置定义写进用户配置

问题：

- 全局 Agent 设置页保存的是合并后的有效态。
- 用户只改一个字段时，所有内置 Agent 都可能被写入用户配置文件。
- 这会让内置升级、用户覆盖和真实自定义项混在一起，后续维护成本很高。

修复：

- 后端 `cc_branch/application/global_agents.py`
  - 返回 `agents`、`builtin_agents`、`user_agents` 三层数据。
- 前端 `apps/web/src/components/GlobalAgentsSettings.tsx`
  - 保存时只序列化和 builtin baseline 不同的字段。
  - 用户自定义 Agent 仍按完整用户定义保存。
- 测试：
  - `apps/web/src/components/GlobalAgentsSettings.test.ts`
  - `tests/test_global_agents.py`

### 2. 清空内置 Agent 字段后会被默认值悄悄恢复

问题：

- 差异化保存后，空字符串字段如果被省略，后端再次合并时会回退到内置默认值。
- 典型场景：用户清空内置 Agent 的 `label_template`，保存后刷新又恢复。

修复：

- `GlobalAgentsSettings.tsx`
  - 对内置 Agent 覆盖保存完整 normalized 值。
  - 当空字符串确实是用户覆盖时，显式写入 `label_template: ''`。
- 测试：
  - `keeps empty-string overrides when users clear a built-in field`

### 3. 内置 Agent 名称可编辑，导致用户心智错误

问题：

- 内置 Agent 名称是稳定 ID，不应该像普通展示名一样编辑。
- 可编辑输入框会让用户以为可以直接改 `codex`、`claude` 这类内置标识。

修复：

- 内置 Agent 的名称输入禁用。
- 删除按钮在内置 Agent 上变成 reset 行为；只有存在覆盖时可用。
- 自定义 Agent 仍可删除。
- 测试：
  - `apps/web/src/components/GlobalAgentsSettings.ui.test.tsx`

### 4. 配置方案确认操作会读取刷新后的错误选中项

问题：

- `ConfigSelector` 打开删除、复制、重命名操作后，确认时仍读取当前 render 的 `selected`。
- 如果配置列表刷新、选中项变化或父组件重渲染，确认按钮可能作用到错误配置。
- 删除配置属于破坏性操作，这个风险必须消除。

修复：

- `apps/web/src/components/ConfigSelector.tsx`
  - 打开操作时保存 `actionTarget` 快照。
  - 删除、复制、重命名确认都使用快照路径。
  - 取消、Escape、关闭弹窗时清理快照。
- 测试：
  - `deletes the config that opened the confirmation even if selection changes`

## 验证证据

本轮本地验证：

```bash
cd apps/web && npm run test -- ConfigSelector
cd apps/web && npm run lint
cd apps/web && npm run test
cd apps/web && npm run build
python3.11 scripts/build-webui.py
python3.11 -m unittest tests.test_global_agents -q
python3.11 -m unittest tests.test_webui tests.test_global_agents -q
python3.11 -m unittest discover tests
python3.11 -m mypy cc_branch
```

远端验证：

- `b886cbf Keep global agent overrides minimal`：CI 通过。
- `73dbd39 Lock built-in agent names in settings`：CI 通过。
- `48fbbc3 Preserve cleared global agent overrides`：CI 通过。
- `e2f55b9 Stabilize workspace config actions`：CI 通过。

## 仍未关闭的风险

### 1. 架构层面还没有完成全局收口

当前已经把部分前端复杂逻辑拆到纯模型和测试中，但 `SlotsSection.tsx` 仍是一个较重的编排组件。下一步应继续把 save patch、selection synchronization、inspector action wiring 拆成更小的可测试单元。

### 2. Dashboard 与空间画布仍需要持续做视觉一致性

Dashboard 已能按 tab group 展示，但它和 Workspace Canvas 的视觉语言仍不是完全同一套组件模型。下一步应优先抽共享的 tab/pane preview primitives，而不是继续在两个页面分别手工调样式。

### 3. Doctor 仍偏“检查报告”，不是完整的 Workspace Health

Doctor 现在能聚合配置和运行时问题，但用户仍需要理解很多底层检查项。下一步应把可修复项、阻塞启动项和纯信息项分层，并让主要修复动作回到同一个工作空间心智里。

## 下一步建议

1. 继续拆 `SlotsSection.tsx` 中的 action orchestration。
2. 抽出 Dashboard / Workspace Canvas 共享的 tab/pane preview 组件。
3. 把 Doctor 信息架构升级为 Health：先显示“现在能不能启动、哪里阻塞、怎么修”，再展开底层检查。
4. 增加浏览器级 UI 回归截图，覆盖 Dashboard、Workspace Canvas、Project Config、Doctor 四个主 tab 的亮色和暗色模式。

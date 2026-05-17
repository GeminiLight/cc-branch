# cc-switch 对 cc-branch 的启发

> 这份文档不讨论“cc-switch 做得强不强”，而是专门回答一个问题：**哪些思路值得 `cc-branch` 借鉴，且不会把我们带偏。**

---

## 先说结论

如果把 `cc-switch` 和 `cc-branch` 放在一起看，我的判断是：

- **cc-switch** 是“多 AI CLI 的统一配置 / 资产 / 会话控制面”
- **cc-branch** 是“项目本地 agent workspace 的声明式执行编排器”

所以我们的最佳策略不是复制它，而是：

> 借它的“统一模型、适配器、状态投影、原子同步”这些底层方法，增强 `cc-branch` 的长期架构。

换句话说：

- 不学它的“大而全”
- 重点学它的“边界划分和同步哲学”

---

## 一、最值得借鉴的 5 个方向

### 1. 从“配置 + 本地 state”升级到“SSOT + runtime projection”

### 现状

我们当前在 `docs/architecture.md` 和 `docs/features.md` 里已经有一个很正确的雏形：

- `.cc-branch.yaml` 描述想要的工作空间形状
- `.cc-branch.state.toml` 保存运行期生成的 session 元数据

这其实已经很接近 cc-switch 的双层思路了。

### 可以继续演进的地方

现在我们的 config/state 更像“单 workspace 内部数据”。  
而 cc-switch 给出的启发是：

- 先定义一个 **内部 canonical model**
- 再把它投影到：
  - tmux session / window
  - agent resume/create command
  - state file
  - 将来可能的 session registry
  - 将来可能的 workspace companion files

### 对 `cc-branch` 的建议

可以逐步把现在的体系明确成：

```text
Workspace Spec (.cc-branch.yaml)
        ↓
Canonical Plan / Runtime Model
        ↓
Projection Targets
  - tmux runtime
  - state file
  - session metadata
  - future workspace assets
```

### 价值

这样以后你要加：
- 非 tmux backend
- 更强的 session restore
- workspace file sync
- Web UI / dashboard

都不会先把现有结构打碎。

**这是我认为最值得吸收的一点。**

---

### 2. 显式做“适配器分层”，不要把差异揉进 planner 里

### cc-switch 给出的启发

它非常明确地承认每个 CLI 工具都不同：
- 有的 additive mode
- 有的 switch mode
- 有的会话在文件里
- 有的会话在 SQLite 里
- 有的 prompt 是独立文件
- 有的配置是 JSON / TOML / YAML / `.env`

它没有试图用一个“过度通用”的接口把差异遮掉，而是通过适配器吃掉差异。

### 对 `cc-branch` 的现实意义

我们当前 `cc-branch` 也已经处在这个拐点：

- 不同 agent 的 `resume_mode` 不同
- `create_mode` 不同
- `label_template` / `resume_template` / `create_template` 不同
- 当前 runtime 基本都投影到 tmux，但未来不一定永远只有 tmux

### 建议的架构方向

把适配边界再拉清楚：

1. **Agent Adapter**  
   负责 session id、label、resume/create 命令生成、能力声明

2. **Backend Adapter**  
   负责 tmux / 未来其他 backend 的窗口、attach、stop、restart

3. **State Projection Adapter**  
   负责把运行结果写入 state、读取 state、校验 state

这样 planner service 就专注于“决策”，而不是混入一堆 CLI 细节和 backend 细节。

---

### 3. 把“原子写入 + 回滚”升级成架构约束，而不是零散实现

### 为什么这点重要

cc-switch 在写 live config 时非常谨慎：
- 先校验
- 原子写入
- 多文件更新支持回滚
- 导入数据库使用临时库验证后再替换

这本质上是在保护用户信任。

### 对 `cc-branch` 的映射

我们虽然没有去改 `~/.codex`、`~/.claude` 这种全局文件，但我们一样会改：
- `.cc-branch.yaml`
- `.cc-branch.state.toml`
- 未来如果做 workspace assets，还会改 `AGENTS.md` / prompt / memory 等

### 建议

把以下原则写进实现约束：

- 所有写 state 的路径统一经过 repository 层
- 覆盖写使用原子 rename / temp file 方案
- 多文件联动变更必须支持“失败后回退”
- `doctor --fix` 和未来 `sync` 类命令要先 dry-run，再 apply

这会让项目显得更“正”，也更适合以后拓展自动修复、批量同步。

---

### 4. 把 session 从“运行副产物”提升成“一等对象”

### 这是 cc-switch 很强的一点

它不是只记录当前 provider，而是认真做 session manager：
- 扫描
- 展示
- 搜索
- 恢复
- 删除
- usage 关联

### 我们当前的问题

`cc-branch` 目前已经保存 session metadata，但更多还是为了支撑：
- resume
- label
- attach / restart / status

它还没有真正把“项目内历史会话”当成可管理对象。

### 这会带来什么新机会

如果我们把 session 提升为一等对象，可以自然长出下面这些能力：

- `cc-branch sessions list`
- `cc-branch sessions show <slot/window>`
- `cc-branch sessions resume <session-id>`
- `cc-branch sessions gc`
- `cc-branch doctor` 对 session/state 漂移做一致性检查

### 为什么这很适合我们

因为我们不是 provider 切换器，我们更关心的是：

> 这个项目里有哪些 agent 会话，它们属于哪个 slot / window / workspace，它们现在能不能恢复。

这比单纯的 tmux 生命周期更贴近“工作空间控制面”。

---

### 5. 把 AGENTS / prompts / memory 看成 workspace asset，而不是仓库外部附件

### cc-switch 给出的重要信号

它已经开始管理：
- prompt files
- skills
- OpenClaw workspace files
- daily memory

这说明成熟工具正在把“AI CLI 周边资产”纳入主产品。

### 对我们特别 relevant 的点

我们项目根目录已经有 `AGENTS.md` 语境，而且用户明确是把这个工具放在多 CLI、多 agent 协作场景里用。

所以对 `cc-branch` 来说，一个很自然的演进方向是：

- 不只定义“开哪些 tmux window”
- 还定义“这个 workspace 应该配哪些 agent companion files”

### 可落地方向

未来可以考虑增加：

```yaml
workspace_assets:
  agents_file: ./AGENTS.md
  prompts_dir: ./.cc-branch/prompts
  memory_dir: ./.cc-branch/memory
  mcp_fragment: ./.cc-branch/mcp.json
```

然后在 `plan` 中把这些资产也解析进来，在 `doctor` 中检查，在 `up` 时选择性同步。

这会让 `cc-branch` 更像“项目级 agent workspace 编排器”，而不是纯 tmux launcher。

---

## 二、按优先级给我们的落地方向

### P0：短期就值得做

### 1. 明确 Runtime Projection 模型

建议在现有 DDD 基础上再收敛出一个更明确的概念：

- `WorkspaceSpec`：配置原文抽象
- `WorkspacePlan`：规划后的执行方案
- `RuntimeProjection`：即将写入 tmux / state / session metadata 的投影结果

这样可以让 `up`、`restart`、`doctor --fix`、未来 `sync` 共用同一套结果，而不是各走各路。

### 2. 整理 Agent Adapter 边界

把不同 agent 的以下逻辑集中到 adapter：
- resume/create 行为
- session_id 来源
- label 规则
- post-launch command 展开
- 未来 session discovery hook

### 3. 给 state 写入加更明确的原子策略

至少要统一保证：
- `.cc-branch.state.toml` 不会半写
- 覆盖更新出错时保留旧文件
- `doctor --fix` / `init --force` 的行为可预测

### 4. 在 `doctor` 里加入“state/runtime 漂移”检查

可以参考 cc-switch 的“live sync consistency”思路，检查：
- state 中记录的 session 是否还存在于 tmux
- tmux 里存在的 window 是否仍匹配 plan
- session_id / label 是否与 agent 规则冲突

这类检查很适合我们现有产品定位，而且价值很高。

---

### P1：中期应该探索

### 5. 增加 `sessions` 子命令族

建议方向：

- `cc-branch sessions list`
- `cc-branch sessions inspect`
- `cc-branch sessions prune`
- `cc-branch sessions restore`

不是去做一个像 cc-switch 那样跨所有外部 CLI 的大而全 session browser，
而是先把 **当前 workspace 里的 session 资产** 做好。

### 6. 增加 import/export/template 能力

cc-switch 的 deeplink 给我们的不是“我们也做 URL protocol”，而是“可分享工作空间模板”这个想法。

对 `cc-branch` 更合适的可能是：

- `cc-branch export template`
- `cc-branch import template`
- `cc-branch init --from <template>`

甚至以后可以再演进到：
- Git repo template
- gist/template registry
- `ccbranch://` 这种 deep link

但前提是先把 canonical model 做稳。

### 7. workspace assets 管理

这是非常像 cc-switch OpenClaw workspace 面板、但更贴近我们的方向：

- 声明某个 workspace 依赖哪些 agent files
- 做 `doctor` 检查缺失文件
- 做 `init` 的 starter scaffold
- 必要时做最小同步，而不是全量接管

如果这个能力做好，`cc-branch` 会明显更有“项目本地协作操作系统”的味道。

---

### P2：长期可以考虑，但现在不建议优先做

### 8. 轻量 Web UI / dashboard 资产面板

cc-switch 的桌面 UI 很强，但我们没必要直接走 Tauri。  
更现实的是：

- 保持 CLI-first
- 如果真要补 UI，优先做轻量本地 Web UI
- 只展示 plan、runtime、sessions、assets、doctor report

这更符合我们当前项目体量和用户预期。

### 9. 本地 registry / sync-ready 存储

等 workspace assets、sessions、template 真做起来后，可以考虑：
- 本地 SQLite registry
- 多 workspace 索引
- 跨项目 session 发现
- 导出 / 备份 / 同步

这一步现在还不急，但架构上可以提前避免把未来路堵死。

---

## 三、哪些不建议学

### 1. 不建议现在复制它的桌面产品形态

cc-switch 是 GUI-first，tray/deeplink/updater/native window 都很合理。  
但 `cc-branch` 当前最强的地方在：
- terminal-native
- tmux-centric
- 声明式 workspace
- 对开发者流程干扰小

如果现在强切到 Tauri，会削弱产品识别度。

### 2. 不建议现在扩成 provider / relay 管理平台

这不是我们的主问题，也会直接把注意力从 workspace orchestration 拉走。

### 3. 不建议照搬 proxy / failover 这条重线

这条线很酷，但工程量巨大，而且和我们当前用户价值并不直接对齐。

### 4. 不建议为了“统一”而过度抽象

cc-switch 的一个优点恰恰是没有把差异抹平。  
我们也一样，不要为了优雅抽象把 agent / backend 的真实差异藏起来，最后把复杂度堆到 planner 里。

---

## 四、我认为最适合 cc-branch 的一句产品升级方向

如果基于这次调研，给 `cc-branch` 提一个更清晰的中期方向，我会这样表述：

> `cc-branch` 不只是在恢复 tmux 布局，它应该逐步成为“项目本地 agent workspace 的控制面”：既能描述工作空间形状，也能管理 session 身份、workspace 资产，以及 agent 运行所需的恢复语义。

这条路和 cc-switch 是互补关系：

- cc-switch 管“跨 CLI 的统一配置控制面”
- cc-branch 管“项目内工作空间的统一执行控制面”

如果走得对，二者甚至可以形成非常自然的边界：
- cc-switch 管全局 CLI 环境
- cc-branch 管仓库内 workspace 编排

---

## 五、我建议我们下一步可以具体讨论的事项

### 方案 A：只做架构收敛，不扩功能面

目标：
- 梳理 canonical model / runtime projection / adapter 边界
- 给现有 tmux-centric 实现做更正规的一层抽象

适合：
- 想先把地基做正
- 暂时不扩命令面

### 方案 B：最小增加 session 管理能力

目标：
- 新增 `sessions` 子命令族
- 强化 state/runtime 一致性
- 让 session 成为用户可感知对象

适合：
- 想让产品价值立刻更上一层
- 又不想引入 UI 和大规模新模块

### 方案 C：引入 workspace assets 概念

目标：
- 把 `AGENTS.md` / prompts / memory / mcp fragment 纳入 workspace 范畴
- 让 `init` / `plan` / `doctor` 能感知这些文件

适合：
- 想把产品从“tmux 编排”推进到“agent workspace 编排”

我个人排序是：

1. **先做 A**：把模型和投影层理顺
2. **再做 B**：把 session 提升为一等对象
3. **最后做 C**：把 workspace assets 纳入主模型

---

## 结论

cc-switch 对我们最大的启发，不是“功能更多”，而是这三个架构判断：

1. **内部统一模型先于外部运行形态**
2. **真实差异通过适配器吸收，不靠硬统一**
3. **用户资产要分层：配置、状态、会话、workspace 文件各有生命周期**

如果我们吸收这三个判断，`cc-branch` 会更像一个正规、长期可扩展的系统；
如果只是学它的 tray、GUI、proxy，那很容易学偏。

---

## 相关参考

- `discussions/cc-switch-analysis.md`
- `discussions/cc-connect-inspirations.md`
- `docs/architecture.md`
- `docs/features.md`

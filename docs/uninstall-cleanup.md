# 卸载与数据清理

本文说明卸载 CC Branch 桌面端后，哪些数据会保留、哪些可以删除，以及如何在界面里找到对应位置。

## 默认行为

卸载应用只会移除桌面端程序本体。CC Branch 不会自动删除你的项目配置、运行状态或全局项目列表，因为这些文件可能是你工作区恢复和排错所需的数据。

## 常见数据位置

| 类型 | 位置 | 建议 |
| --- | --- | --- |
| 工作区配置 | `<project>/.cc-branch/config.yaml` | 可以提交到项目仓库，记录工作区布局和 Agent 配置。 |
| 本机运行状态 | `<project>/.cc-branch/state.yaml` | 不建议提交；删除后会丢失本机绑定的会话状态，但配置仍在。 |
| 多状态目录 | `<project>/.cc-branch/states/` | 不建议提交；用于多配置或本机运行状态。 |
| 全局项目列表 | `~/.cc-branch/app/projects.yaml` | 记录侧边栏项目、当前项目和排序。 |
| 全局 Agent 定义 | `~/.cc-branch/agents.yaml` | 记录本机通用 Agent 覆盖配置。 |
| 本地日志 | `~/.cc-branch/logs/`、系统应用日志目录 | 用于排错；可在确认不再需要后删除。 |

桌面端的系统应用数据目录由操作系统管理。不同平台路径不同，建议优先在应用内打开“设置 -> 本地数据”，使用“显示位置”查看当前机器上的实际路径。

## 只卸载应用

1. 退出 CC Branch。
2. macOS：从 `Applications` 删除 `cc-branch.app`。
3. Windows：从“设置 -> 应用”卸载 CC Branch。
4. Linux：按你安装的包格式卸载，例如删除 AppImage，或使用系统包管理器卸载 `.deb` / `.rpm`。

这样不会删除项目里的 `.cc-branch/config.yaml` 和 `.cc-branch/state.yaml`。

## 完整清理本机数据

只有在确认不再需要恢复工作区状态时再执行这一步。

```bash
rm -rf ~/.cc-branch/app
rm -f ~/.cc-branch/agents.yaml
rm -rf ~/.cc-branch/logs
```

如果也想删除某个项目的 CC Branch 配置和状态：

```bash
rm -rf /path/to/project/.cc-branch
```

删除整个项目 `.cc-branch` 会同时移除 `config.yaml`。如果你只想重置本机运行状态，优先删除 `state.yaml` 和 `states/`，保留 `config.yaml`。

## 生成排错材料

诊断页里的“复制报告”会生成脱敏后的诊断 bundle，包含版本、当前项目、配置/状态文件信息、doctor 结果和最近日志摘要。报告会把用户主目录替换为 `~`，方便发给维护者排查。

<!-- Last verified: 2026-06-11 | Current stage: reference research | Source commit: 2f7ef136de28e006f6b55af224b29a1ff8b5a1bf -->

# Basic Memory

## 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) |
| 语言 | Python |
| License | AGPL-3.0 |
| 调研快照 | `2f7ef136de28e006f6b55af224b29a1ff8b5a1bf`，2026-06-10 |
| 一句话定位 | 用 Markdown、知识图谱、搜索和 MCP 给不同 Agent 客户端提供同一套长期记忆。 |

## 解决的问题

不同 Agent CLI 的上下文窗口、会话记忆和插件生态都不一样。Basic Memory 试图把“项目长期记忆”从某个聊天窗口里拿出来，变成人和 Agent 都能读写的 Markdown 文件，再用数据库和 MCP 暴露给 Claude Code、Codex、Cursor、ChatGPT 等客户端。

## 架构方案

Basic Memory 有三个入口：

- **API**：FastAPI REST server。
- **MCP**：给 LLM/Agent 客户端调用。
- **CLI**：Typer 命令行。

整体流向：

```text
Markdown files
  -> sync / watch
  -> parser
  -> Entity / Observation / Relation
  -> SQLite or Postgres
  -> FTS / vector search
  -> MCP tools / API / CLI
```

每个入口有自己的 composition root，统一通过 config、runtime mode、service/repository layer 组装依赖。

## Markdown 知识模型

Markdown 是源文件。一个 note 可以包含：

- YAML frontmatter：title、type、tags、permalink、schema 和自定义 metadata。
- Observations：`- [category] content #tag` 形式的原子事实。
- Relations：`- relation_type [[Target]]` 或正文 wiki link。
- Permalink：稳定引用，可以形成 `memory://` URL。

数据库里对应的核心模型包括 Entity、Observation、Relation、NoteContent。文件 path、checksum、mtime、size 被用于同步和变更检测。

## 搜索和记忆召回

Basic Memory 支持：

- Full-text search：SQLite FTS5 或 Postgres tsvector。
- Vector search：本地 FastEmbed、OpenAI embeddings 或 LiteLLM provider。
- Hybrid retrieval：组合关键词精确性和语义召回。
- `build_context`：围绕某个 `memory://` 目标构造关联上下文。
- `recent_activity`：查看近期活动。

MCP tools 包括 `search_notes`、`read_note`、`write_note`、`edit_note`、`build_context`、`recent_activity`、`list_directory`、`move_note`、`delete_note`、workspace/project 管理等。

## Agent 插件

Basic Memory 不只是提供 MCP server，还提供针对 Agent host 的插件：

- **Claude Code plugin**：SessionStart hook 读取 active tasks、recent work，PreCompact hook 写 session checkpoint；还提供 `/basic-memory:bm-setup`、`:remember`、`:share`、`:status`。
- **Codex plugin**：`bm-orient`、`bm-checkpoint`、`bm-decide`、`bm-remember`、`bm-share`、`bm-status`，并通过 SessionStart/PreCompact hook 注入 brief 和写 checkpoint。

这证明“记忆”不只是搜索工具，而是可以嵌入 Agent 生命周期：开始时定向、过程中记录决策、压缩前保存现场。

## 对 CC Branch 的启发

- CC Branch 不需要内置完整知识图谱，但可以为项目配置外部 memory provider。
- workspace 恢复时可以调用 MCP memory：先读 recent activity / active task，再打开 Agent panes。
- `pre-compact checkpoint` 的思想可以迁移成 `cc-branch snapshot` 或 `stop` 时的可选保存动作。
- README、wiki、`.cc-branch/config.yaml` 与外部记忆之间要有清晰边界：配置负责恢复环境，记忆负责恢复上下文。

## 局限和风险

- Basic Memory 的产品范围大于 CC Branch：它是知识库/记忆系统，不是终端工作台。
- Python、MCP、watch service、embedding 依赖会增加安装和调试成本。
- Team/cloud 能力涉及权限、同步和计费，不应混入 CC Branch 的本地核心路径。

## 可参考实现点

- Markdown 作为人类可编辑的记忆源文件。
- `Entity / Observation / Relation` 三层模型。
- SessionStart brief 和 PreCompact checkpoint。
- search tools 的多模式：text、vector、hybrid、metadata filters。
- WatchService 对项目目录变更做 debounce 和 sync。

## 证据来源

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/NOTE-FORMAT.md`
- `docs/semantic-search.md`
- `plugins/claude-code/README.md`
- `plugins/codex/README.md`
- `src/basic_memory/models/knowledge.py`
- `src/basic_memory/services/search_service.py`
- `src/basic_memory/sync/sync_service.py`
- `src/basic_memory/sync/watch_service.py`
- `src/basic_memory/mcp/tools/*`

# AGENTS.md — StataAgent 工作流

## 会话开始

1. 运行 `git log --oneline -10` 并阅读 `claude-progress.md` 以了解当前状态。
2. 阅读 `feature_list.json`，选择最高优先级的未完成功能（遵循 governance 中的 `task_ordering`）。
3. 在编写任何代码前，宣布将要处理的功能。

## 开发期间

- **一次处理一个功能**。不要批量处理多个功能。
- 不要删除或编辑 `feature_list.json` 中的功能定义。只能修改 `status` 和 `passes` 字段。

## 会话结束

1. **自验证**：端到端测试功能。仅在确认功能正常后设置 `"passes": true`。
2. **Git 提交**：提交所有更改并附带描述性消息。
3. **更新进度**：更新 `claude-progress.md` 作为紧凑的交接文件。覆盖 `CURRENT CONTEXT`，仅在这些事实实质性变化时更新 `PROJECT STATUS`、`ARCHITECTURE DECISIONS` 或 `KNOWN ISSUES`。不要在其中保留逐会话的日志。

## 仓库导航

- `AGENTS.md`：会话工作流和仓库导航入口点。
- `ARCHITECTURE.md`：顶层架构、固定目录结构和分层边界。
- `Requirements.md`：产品需求和五阶段实证分析流程。
- `feature_list.json`：分阶段待办事项和验证状态。
- `claude-progress.md`：紧凑的跨会话交接、架构决策和当前工作上下文。
- `docs/README.md`：文档中心、阅读顺序和单一事实来源索引。
- `docs/engineering/agent-harness.md`：Agent 编码、架构和代码风格的强制约束设计。
- `docs/product/research-workflow.md`：阶段语义、运行状态机和失败检查点。
- `docs/references/CSMAR_PYTHON.md`：供应商 SDK 参考材料和使用约束。

## 项目文档目录结构

```text
.
├── AGENTS.md
├── ARCHITECTURE.md
├── Requirements.md
├── feature_list.json
├── claude-progress.md
└── docs/
    ├── README.md
    ├── engineering/
    │   └── agent-harness.md
    ├── product/
    │   └── research-workflow.md
    └── references/
        ├── CSMAR_PYTHON.md
        └── Harness-engineering.md
```

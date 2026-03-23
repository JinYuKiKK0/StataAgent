# StataAgent 文档

仓库文档是代理上下文的系统记录。`AGENTS.md` 保持简短并指向此处；更深入的知识存在于具有清晰主题边界的专注文档中。

## 阅读顺序

1. `AGENTS.md`
2. `claude-progress.md`
3. `feature_list.json`
4. `ARCHITECTURE.md`
5. `docs/context-harness.md`
6. `docs/product/research-workflow.md`
7. 当任务涉及产品规则或供应商约束时，`Requirements.md` 或 `docs/references/CSMAR_PYTHON.md`

## 单一事实来源

- 会话工作流和仓库地图：`AGENTS.md`
- 架构和技术栈：`ARCHITECTURE.md`
- 上下文容器约定：`docs/context-harness.md`
- 研究阶段语义：`docs/product/research-workflow.md`
- 产品需求基线：`Requirements.md`
- 供应商 SDK 约束：`docs/references/CSMAR_PYTHON.md`
- 紧凑的跨会话交接：`claude-progress.md`

## 最小知识库

本仓库当前故意保持文档知识库较小：

- `docs/README.md`
- `docs/context-harness.md`
- `docs/product/research-workflow.md`
- `docs/references/CSMAR_PYTHON.md`

仅当知识足够稳定，能够超越单个任务或会话时，才添加新文档。

## 已退役的根计划

`PLAN.md` 已退役。持久的架构内容现在位于 `ARCHITECTURE.md` 中，域工作流上下文位于 `docs/` 下。

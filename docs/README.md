# StataAgent 文档

仓库文档是代理上下文的系统记录。`AGENTS.md` 保持简短并指向此处；更深入的知识存在于具有清晰主题边界的专注文档中。

## 上下文容器模型

本仓库使用上下文容器模型：

- `AGENTS.md` 是地图，不是百科全书。
- `ARCHITECTURE.md` 是顶层技术单一事实来源。
- `docs/` 保存代理按需渐进式发现的持久知识。

目标是保持注入上下文小而稳定、可导航，同时按需提供更深入知识。

## 阅读顺序

1. `AGENTS.md`
2. `claude-progress.md`
3. `feature_list.json`
4. `ARCHITECTURE.md`
5. `docs/README.md`
6. `docs/product/research-workflow.md`
7. 当任务涉及产品规则或供应商约束时，`Requirements.md` 或 `docs/references/CSMAR_PYTHON.md`

## 渐进式披露

代理应分层遍历知识库：

1. 阅读 `AGENTS.md` 了解工作流和导航。
2. 阅读 `claude-progress.md` 了解紧凑的当前会话状态。
3. 阅读 `feature_list.json` 了解任务排序和通过标准。
4. 阅读 `ARCHITECTURE.md` 了解系统边界和运行时职责。
5. 仅阅读当前任务所需的专注文档。

## 单一事实来源

- 会话工作流和仓库地图：`AGENTS.md`
- 架构和技术栈：`ARCHITECTURE.md`
- 上下文容器约定：`docs/README.md`
- 研究阶段语义：`docs/product/research-workflow.md`
- 产品需求基线：`Requirements.md`
- 供应商 SDK 约束：`docs/references/CSMAR_PYTHON.md`
- 紧凑的跨会话交接：`claude-progress.md`

## 文档编写规则

- 保持 `AGENTS.md` 简短。添加链接和边界，而不是论文。
- 将架构决策集中在 `ARCHITECTURE.md`。
- 按主题拆分持久知识，避免再引入单一大而全计划文档。
- 每个主题保留单一事实来源；交叉链接而不是复制。
- 保持 `claude-progress.md` 紧凑，不在其中附加逐会话叙述；按时间线依赖 git 历史。
- 文档与代码或活动设计不一致时，立即更新或删除。

## 最小知识库

本仓库当前故意保持文档知识库较小：

- `docs/README.md`
- `docs/product/research-workflow.md`
- `docs/references/CSMAR_PYTHON.md`

仅当知识足够稳定，能够超越单个任务或会话时，才添加新文档。

## 何时添加新文档

仅当满足以下至少一个条件时才创建新文档：

- 知识需要在多个会话中复用。
- 主题具有稳定所有权和清晰边界。
- 否则重复读取相同上下文会让 `AGENTS.md` 或 `ARCHITECTURE.md` 膨胀。

否则，将信息保留在任务本地注释或进度日志中。

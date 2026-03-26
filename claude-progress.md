# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S2（理论预判与模型构建）
- 总体进度：3/18 features 完成（S1-T1、S1-T2、S1-T3）
- 最后更新：2026-03-26
- 阻塞问题：无；下一优先任务为 `S2-T1`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：将 `docs/product/empirical-analysis-workflow-v2.md` 升格为正式工作流基线，并为正式文档补入 Mermaid 状态机执行链路；当前 `v2` 与正式基线文档内容保持一致
- 阶段：S2 进行中（`S2-T1` 仍是下一优先功能）；本次仅更新工作流基线文档与交接，不变更业务实现与 feature 状态
- 分支：main
- 关键文件：
  - `docs/product/empirical-analysis-workflow-v2.md` — 已补入 Mermaid 状态机执行链路，并作为正式基线内容的编辑源
  - `docs/product/empirical-analysis-workflow.md` — 当前产品流程单一事实来源；现已完全替换为与 `v2` 一致的工作流定义
  - `AGENTS.md` — 会话工作流和项目 skill 入口；本次按其要求补充交接
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 真实 Tongyi API 需要用户在 `.env` 中提供可用的 `DASHSCOPE_API_KEY`；当前验证以注入式测试替身覆盖，不包含线上密钥调用
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

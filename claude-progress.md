# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：3/24 features 完成（S1-T1、S1-T2、S1-T3）
- 最后更新：2026-03-26
- 阻塞问题：无；下一优先任务为 `S1-T4`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：简化 `feature_list.json` 结构，移除冗余治理字段（priority, creation_order, status, updated_at），以 `passes` 字段作为唯一进度标识。
- 阶段：S1（需求解析与最低可行数据契约）
- 分支：main
- 关键文件：
  - `feature_list.json` — 已移除冗余字段，保留 `passes` 作为核心进度。下一优先任务按列表顺序为 `S1-T4`（CSMAR 探针级变量映射）。
  - `docs/product/empirical-analysis-workflow.md` — 当前产品流程单一事实来源。
  - `AGENTS.md` — 会话工作流逻辑；现在按照列表顺序选择下一项。
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 真实 Tongyi API 需要用户在 `.env` 中提供可用的 `DASHSCOPE_API_KEY`；当前验证以注入式测试替身覆盖，不包含线上密钥调用
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

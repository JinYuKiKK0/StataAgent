# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：5/24 features 完成（S1-T1、S1-T2、S1-T3、S1-T4、S1-T5）
- 最后更新：2026-03-26
- 阻塞问题：无；下一优先任务为 `S1-T6`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：完成 `S1-T5`（探针执行与覆盖摘要）全链路落地，新增 queryCount 探针、覆盖摘要契约、探针执行服务与编排节点。
- 阶段：S1（需求解析与最低可行数据契约）
- 分支：main
- 关键文件：
  - `feature_list.json` — `S1-T5` 已设置 `passes: true`；下一优先任务按列表顺序为 `S1-T6`（最低可行数据契约构建）。
  - `src/stata_agent/domains/fetch/types.py` — 新增 `VariableProbeResult` 与 `ProbeCoverageResult` 契约。
  - `src/stata_agent/providers/csmar.py` — 新增 `query_count` 探针能力和可注入覆盖行为。
  - `src/stata_agent/services/probe_executor.py` — 实现探针执行、覆盖率汇总与 Hard fail-fast 决策。
  - `src/stata_agent/workflow/orchestrator.py` — 新增 `probe_coverage` 节点并推进到 `RunStage.PROBED`。
  - `src/stata_agent/workflow/state.py` / `src/stata_agent/workflow/types.py` — 增加探针摘要状态字段与 `PROBED` 阶段。
  - `tests/test_probe_executor.py` / `tests/test_workflow_orchestrator.py` — 补齐 S1-T5 核心路径测试。
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

# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：7/24 features 完成（S1-T1~S1-T7）
- 最后更新：2026-04-06
- 阻塞问题：无；产品待办仍以下一项 `S2-T1` 理论预期与基准方程摘要为主

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 本会话完成：将 S1 从阶段内手工串联重构为真正的 LangGraph 子图
  - `src/stata_agent/workflow/stages/phase1_feasibility.py` 现在是兼容门面，内部调用编译后的 S1 子图
  - `src/stata_agent/workflow/stages/phase1_feasibility_nodes.py` 显式暴露 7 个节点：`parse_request`、`build_variable_requirements`、`plan_probe_mapping`、`materialize_variable_bindings`、`run_field_probes`、`summarize_probe_coverage`、`build_data_contract`
  - `src/stata_agent/workflow/state.py` 新增 `mapping_plan_result`、`probe_results_raw`、`node_audits`
  - `src/stata_agent/workflow/observability.py` 与 `src/stata_agent/workflow/state_contracts.py` 提供节点审计和显式状态更新契约
- 服务拆分但保持兼容：
  - `src/stata_agent/services/variable_mapper.py` 拆为 `plan_probe_mapping()` 与 `materialize_variable_bindings()`，保留 `map_probe_bindings()` 包装
  - `src/stata_agent/services/probe_executor.py` 拆为 `run_field_probes()` 与 `summarize_coverage()`，保留 `execute_coverage()` 包装
- 根图与入口调整：
  - `src/stata_agent/workflow/graph.py` 仍保持阶段级拓扑，不把 S1 节点摊平到根图
  - `src/stata_agent/workflow/orchestrator.py` 与 `src/stata_agent/workflow/ports.py` 透传 `RunnableConfig`，让父图 trace/checkpoint 能贯穿 S1 子图
  - `src/stata_agent/interfaces/cli.py` 的 Gateway 呈递逻辑已拆到 `src/stata_agent/interfaces/gateway_cli.py`，用于通过仓库 line-budget 约束
- 测试结果：
  - `uv run python -m tools.run_quality_gates` ✅
  - `uv run pytest tests/s1_feasibility tests/core_workflow tests/entrypoints -q` ✅（47 passed, 15 skipped）
- 当前阶段：产品总体阶段不变，`feature_list.json` 未改动，S2 待办顺序不变
- 分支：main
- 关键文件：
  - `src/stata_agent/workflow/stages/phase1_feasibility.py`
  - `src/stata_agent/workflow/stages/phase1_feasibility_nodes.py`
  - `src/stata_agent/workflow/observability.py`
  - `src/stata_agent/workflow/state_contracts.py`
  - `tests/s1_feasibility/test_phase1_subgraph.py`
  - `tests/s1_feasibility/test_phase1_subgraph_fail_fast.py`
  - `tests/core_workflow/test_workflow_subgraph_streaming.py`
- 工作树额外状态：
  - 用户已有未纳入本次提交的改动：`CR_Problem.md` 已修改，`PLAN.md` 已删除
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 架构决策

- S1 保持为根图中的单个阶段节点，但阶段内部改为 LangGraph 子图；这样既保留产品语义，又把 LangSmith 可观测性下沉到节点级
- 节点调试信息统一放入 `node_audits`，完整供应商 trace 继续保留在 `csmar_traces`；审计对象只保存摘要和 trace 引用，不复制大对象
- 映射与探针服务采用“两段式内部 API + 兼容包装”的方式演进，避免破坏现有调用方和测试心智

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

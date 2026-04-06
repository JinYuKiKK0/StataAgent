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

- 本会话完成：为 S1 子图重构做收尾清理，移除遗留兼容层与重构专用测试
  - `src/stata_agent/services/variable_mapper.py` 已移除旧包装 `map_probe_bindings()`；调用方统一走 `plan_probe_mapping()` + `materialize_variable_bindings()`
  - `src/stata_agent/services/probe_executor.py` 已移除旧包装 `execute_coverage()`；调用方统一走 `run_field_probes()` + `summarize_coverage()`
  - `src/stata_agent/workflow/ports.py` 已同步删除上述遗留接口
  - `src/stata_agent/workflow/stages/phase1_feasibility.py` 已删除仅供重构测试使用的 phase-level `compiled_graph` 暴露以及无用成员保存
- 已删除的重构专用测试/支撑文件：
  - `tests/s1_feasibility/phase1_subgraph_artifacts.py`
  - `tests/s1_feasibility/phase1_subgraph_support.py`
  - `tests/s1_feasibility/test_phase1_subgraph.py`
  - `tests/s1_feasibility/test_phase1_subgraph_fail_fast.py`
  - `tests/core_workflow/test_workflow_subgraph_streaming.py`
- 保留的 S1 功能测试已改成直接使用现行 API：
  - `tests/s1_feasibility/test_t4_variable_mapper_core.py`
  - `tests/s1_feasibility/test_t4_variable_mapper_live.py`
  - `tests/s1_feasibility/test_t5_probe_executor.py`
  - `tests/s1_feasibility/test_t5_probe_executor_live.py`
- 测试结果：
  - `uv run python -m tools.run_quality_gates` ✅
  - `uv run pytest tests/s1_feasibility tests/core_workflow tests/entrypoints -q` ✅（38 passed, 15 skipped）
- 当前阶段：产品总体阶段不变，`feature_list.json` 未改动，S2 待办顺序不变
- 分支：main
- 关键文件：
  - `src/stata_agent/services/variable_mapper.py`
  - `src/stata_agent/services/probe_executor.py`
  - `src/stata_agent/workflow/ports.py`
  - `src/stata_agent/workflow/stages/phase1_feasibility.py`
- 工作树额外状态：
  - 用户已有未纳入本次提交的改动：`CR_Problem.md` 已修改，`PLAN.md` 已删除
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 架构决策

- S1 保持为根图中的单个阶段节点，但阶段内部改为 LangGraph 子图；这样既保留产品语义，又把 LangSmith 可观测性下沉到节点级
- 节点调试信息统一放入 `node_audits`，完整供应商 trace 继续保留在 `csmar_traces`；审计对象只保存摘要和 trace 引用，不复制大对象
- 映射与探针服务现已收口到“两段式 API”本身，不再保留旧包装；仓库内调用和测试都直接围绕现行节点边界组织

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

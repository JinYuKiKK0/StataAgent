# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：7/24 features 完成（S1-T1~S1-T7）
- 最后更新：2026-03-28
- 阻塞问题：无；S1 阶段圆满完成，即将进入 S2 阶段（核心为 `S2-T1` 理论预期与基准方程摘要）

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 本会话完成：启动 IC5（Implementation Changes 5）在 StataAgent 的首轮落地，完成“表标识统一 + 本地 trace 审计”主线改造。
  - 契约迁移：`table_name(查询语义) -> table_code`，`csmar_database -> database_name`，并保留 `table_name` 作为展示字段。
  - 类型升级：`src/stata_agent/domains/mapping/types.py` 新增 `CsmarToolTrace`，`VariableBinding` 增加 `trace_id`；`src/stata_agent/domains/fetch/types.py` 的 `QueryPlan/VariableProbeResult` 切到 `table_code`。
  - 状态升级：`src/stata_agent/workflow/state.py` 新增 `csmar_traces`，用于聚合 provider 工具调用审计。
  - provider 收口：`src/stata_agent/providers/csmar/client.py` 修复 `table_code=request.table_name` 旧桥接，改为严格 `table_code` 入参，并新增本地 trace 记录/回收（`drain_tool_traces`）。
  - S1 链路：`variable_mapper.py`、`probe_executor.py`、`phase1_feasibility.py` 打通 trace 传播（provider -> component -> `ResearchState`），并将 binding/probe 结果主键统一为 `table_code`。
  - LLM 判别：`providers/llm.py` 改为 `selected_table_code`，候选 payload 显式区分 `table_code` 与展示 `table_name`。
  - 相关测试：更新 `tests/s1_feasibility` 契约断言，并在 `test_csmar_bridge_mcp_adapter.py` 新增 provider 本地 trace 回收用例；`tests/architecture/test_boundary_contracts.py` 新增 `csmar_traces` 契约断言。
- 验证结果：
  - `uv run pytest tests/s1_feasibility/test_csmar_bridge_mcp_adapter.py tests/s1_feasibility/test_t4_variable_mapper_core.py tests/s1_feasibility/test_t4_variable_mapper_budget.py tests/s1_feasibility/test_t5_probe_executor.py tests/s1_feasibility/test_t6_data_contract_builder.py tests/architecture/test_boundary_contracts.py -q` ✅（18 passed, 2 skipped）
  - `uv run python -m pyright src/stata_agent` ✅（0 errors）
  - `uv run python -m tools.run_quality_gates` ✅（ruff/pyright/import-linter/architecture/harness 全通过）
- 当前阶段：S1 回炉增强（IC5 契约统一）进行中；`feature_list.json` 未改动，S2 排序保持不变。
- 分支：main

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

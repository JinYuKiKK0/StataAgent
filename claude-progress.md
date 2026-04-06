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

- 本会话完成：落地 S1 内部组织架构重构，按能力域重组 `services/`，把 `workflow/` 收缩为编排层，把 provider DTO/trace 下沉到 `providers/`
- 新增目录与模块：
  - `src/stata_agent/services/spec/`
  - `src/stata_agent/services/mapping/`
  - `src/stata_agent/services/probe/`
  - `src/stata_agent/services/contract/`
  - `src/stata_agent/providers/llm/`
  - `src/stata_agent/domains/contract/`
  - `src/stata_agent/workflow/bootstrap.py`
  - `src/stata_agent/workflow/gateway.py`
- `ResearchState` 已改为分组产物结构：`phase1_artifacts`、`workflow_audit`、`gateway_state`
- Phase 1 编排已拆成更清晰的职责边界：
  - 映射：`plan_probe_mapping()` + `materialize_variable_bindings()`
  - 探针：`run_field_probes()` + `summarize_coverage()`
  - 审计与状态更新辅助逻辑已移到 `workflow/stages/phase1_audit.py` 与 `phase1_state_updates.py`
- 已删除遗留与空壳模块：
  - `src/stata_agent/workflow/ports.py`
  - `src/stata_agent/providers/llm.py`
  - `src/stata_agent/providers/llm_mapping.py`
  - `src/stata_agent/providers/llm_mapping_toolkit.py`
  - `src/stata_agent/services/requirement_parser.py`
  - `src/stata_agent/services/variable_requirements_builder.py`
  - `src/stata_agent/services/variable_mapper.py`
  - `src/stata_agent/services/probe_executor.py`
  - `src/stata_agent/services/data_contract_builder.py`
  - `src/stata_agent/services/model_planner.py`
  - `src/stata_agent/services/panel_builder.py`
  - `src/stata_agent/services/quality_gate.py`
  - `src/stata_agent/services/result_judge.py`
  - `src/stata_agent/workflow/stages/phase2_modeling.py`
  - `src/stata_agent/workflow/stages/phase3_execution.py`
- 测试结果：
  - `uv run python -m tools.run_quality_gates` ✅
  - `uv run pytest tests/s1_feasibility tests/core_workflow tests/entrypoints tests/architecture -q -m 'not live_api'` ✅（45 passed, 15 deselected）
- 当前阶段：产品总体阶段不变，`feature_list.json` 未改动，S2 待办顺序不变
- 分支：main
- 关键文件：
  - `src/stata_agent/workflow/bootstrap.py`
  - `src/stata_agent/workflow/state.py`
  - `src/stata_agent/workflow/stages/phase1_feasibility_nodes.py`
  - `src/stata_agent/providers/llm/variable_mapping_planner.py`
  - `src/stata_agent/providers/csmar/types.py`
- 工作树额外状态：
  - 用户已有未纳入本次提交的改动：`CR_Problem.md` 已修改，`PLAN.md` 已删除
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 架构决策

- `workflow/` 只保留编排、状态推进、Gateway 和组合根；对象装配集中到 `workflow/bootstrap.py`
- `services/` 以能力域组织，并在域内区分 `contracts`、`ports`、use case 实现；provider 只允许依赖 service 契约，不允许依赖 service 实现
- `domains/` 只保留稳定边界契约；`DataContractBundle` 已归位到 `domains/contract`，`domains/spec` 与 `domains/mapping` 已清退过程性 DTO
- 节点调试信息统一放入 `workflow_audit.node_audits`，完整供应商 trace 保留在 `workflow_audit.csmar_traces`

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

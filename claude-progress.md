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

- 本会话完成：落地 S1 LangGraph 上下文膨胀治理，active state 改为“当前工作集 + 最终契约”，完整 LLM/CSMAR 原始审计已从 state 侧移到 audit store
- 新增模块：
  - `src/stata_agent/services/audit/`
  - `src/stata_agent/providers/audit/`
  - `src/stata_agent/workflow/stages/phase1_selectors.py`
  - `src/stata_agent/workflow/stages/phase1_threading.py`
- `ResearchState.phase1_artifacts` 已瘦身：
  - 移除 `parse_result`、`mapping_plan_result`、`mapping_result`、`probe_results_raw`
  - S1 完成后仅保留 `data_contract_bundle`，其余中间产物从 active state 清理
- 节点输入契约已显式化：
  - 映射规划改用 `MappingPlannerInput`
  - probe 执行改用 `ProbeExecutionInput`
  - `VariableBindingMaterializer` 与 `DataContractBuilder` 不再回读原始 `ResearchRequest`
- 业务 DTO 已瘦身：
  - `VariableBinding` 只保留 probe/contract 必要字段
  - `DataContractBundle` 不再复制 `spec`、`variable_definitions`、`variable_bindings`、原始 probe 明细
  - Gateway payload 不再携带 `mapping_evidence_summary` / `probe_trace_summary`
- 可观测性路径：
  - `WorkflowNodeAudit` 现在记录 `audit_refs` / `trace_refs`
  - `ApplicationOrchestrator` 新增 `read_audit_record()` / `read_trace_record()` 调试入口
  - LangGraph runtime 有 store 时走 `StoreBackedAuditStore`；本地/测试默认 `InMemoryAuditStore`
- 兼容与验证：
  - `packages/stata-executor` 增加 POSIX 下 `.cmd/.bat` fake executable 兼容分支，保证跨平台测试夹具可运行
  - `uv run pytest -q` ✅（73 passed, 12 skipped）
  - `uv run python -m tools.run_quality_gates` ✅
- 当前阶段：产品阶段不变，`feature_list.json` 未改动，S2 下一项仍是 `S2-T1`
- 分支：main
- 关键文件：
  - `src/stata_agent/workflow/state.py`
  - `src/stata_agent/workflow/stages/phase1_feasibility_nodes.py`
  - `src/stata_agent/workflow/stages/phase1_selectors.py`
  - `src/stata_agent/providers/audit/store.py`
  - `src/stata_agent/domains/contract/types.py`
  - `src/stata_agent/providers/llm/variable_mapping_planner.py`
- 开发服务器：不适用

## 架构决策

- `workflow/` 只保留编排、状态推进、Gateway 和组合根；对象装配集中到 `workflow/bootstrap.py`
- `services/` 以能力域组织，并在域内区分 `contracts`、`ports`、use case 实现；provider 只允许依赖 service 契约，不允许依赖 service 实现
- `domains/` 只保留稳定边界契约；`DataContractBundle` 已归位到 `domains/contract`，`domains/spec` 与 `domains/mapping` 已清退过程性 DTO
- 节点调试信息只在 `workflow_audit.node_audits` 中保留摘要与引用；完整 raw response / mapping plan / probe result / provider trace 统一落到 audit store，不再常驻 workflow state

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

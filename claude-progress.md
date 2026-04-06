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

- 本会话完成：重做 Phase1 频率契约、变量映射节点和节点级 CSMAR 客户端治理。
  - `src/stata_agent/domains/spec/types.py`、`services/requirement_parser.py`、`providers/llm.py`：`ResearchSpec` 新增 `analysis_frequency_hint`；频率推断前移到 `_parse_request_node` 对应链路，parser 会归一化为 `annual/quarterly/monthly/unknown`。
  - `src/stata_agent/services/variable_requirements_builder.py`：删除 builder 内部频率猜测逻辑；所有 `VariableDefinition.frequency_hint` 直接复制 `spec.analysis_frequency_hint`。
  - `src/stata_agent/domains/mapping/types.py`、`ports.py`：新增 `CsmarTableRecord`、`VariableMappingPlanItem/Result`、LLM toolkit 返回契约模型；`CsmarMetadataProviderPort` 改为 `list_databases/list_tables/get_table_schema/probe_field_availability` 形状。
  - `src/stata_agent/providers/csmar/node_scoped_client.py`：新增节点级 provider wrapper，执行工具白名单与预算限制；预算耗尽返回 `budget_exhausted`，并生成本地 trace。
  - `src/stata_agent/providers/llm_mapping.py`、`providers/llm_mapping_toolkit.py`：新增 `TongyiVariableMappingPlanner`，通过 `create_agent()` 只暴露 `csmar_list_databases`、`csmar_list_tables`、`csmar_get_table_schema` 三个工具。
  - `src/stata_agent/services/variable_mapper.py`：不再走 `search_tables/search_fields + semantic_judge` 路径，改为消费 planner 的结构化映射结果；旧 `mapping_candidate_builder.py` 已删除。
  - `src/stata_agent/workflow/orchestrator.py`、`tests/live_api_support.py`：默认映射依赖切到 `TongyiVariableMappingPlanner`。
- 测试同步：
  - 新增 `tests/s1_feasibility/test_t2_requirement_parser_core.py`，覆盖研究级频率契约。
  - 新增 `tests/s1_feasibility/test_t4_node_scoped_csmar_provider.py`，覆盖节点级白名单和 `budget_exhausted`。
  - 重写 `tests/s1_feasibility/test_t4_variable_mapper_core.py` 为 planner 结果装配语义；删除旧 `test_t4_variable_mapper_budget.py`。
- 测试结果：
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/s1_feasibility -q -m 'not live_api'` ✅（28 passed, 8 deselected）
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests -q -m 'not live_api'` ✅（43 passed, 15 deselected）
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python -m pyright` ✅
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python -m tools.run_quality_gates` ⚠️：`ruff` / `pyright` / `import-linter` / `architecture` 通过；`tools.harness lint` 仅剩仓库既有问题 `src/stata_agent/interfaces/cli.py` 超过 350 行，非本会话引入。
- 当前阶段：产品总体阶段仍是 S1 已交付后回炉增强；`feature_list.json` 未改动，S2 待办顺序不变。
- 分支：main
- 关键文件：
  - `src/stata_agent/providers/llm_mapping.py`、`src/stata_agent/providers/llm_mapping_toolkit.py` — 新的映射 LLM planner 与最小工具面。
  - `src/stata_agent/providers/csmar/node_scoped_client.py` — 节点级工具白名单与预算执行器。
  - `src/stata_agent/services/variable_mapper.py` — planner 结果到 `VariableBinding` 的装配逻辑。
  - `src/stata_agent/domains/spec/types.py`、`src/stata_agent/services/requirement_parser.py` — 研究级频率契约。
- 未解决的问题：
  - 当前环境缺少 `RUN_LIVE_API_TESTS=1` 与完整 CSMAR/Tongyi live 配置，因此真实 E2E 仅保留 smoke 测试代码，未在本会话执行。
  - `src/stata_agent/interfaces/cli.py` 仍触发既有 `SA4002` 文件超长告警；若要让统一质量门全绿，需要单独拆分 CLI 文件。
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

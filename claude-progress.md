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

- 本会话完成：启动 IC4 落地，实现 S1-T4 显式两阶段映射并清理 provider legacy 路径。
  - `src/stata_agent/domains/mapping/ports.py`：`CsmarMetadataProviderPort` 改为显式能力接口（`search_tables/get_table_schema/search_fields/probe_field_availability`）。
  - `src/stata_agent/domains/mapping/types.py`：新增表候选/schema/辅助检索/预算 DTO 与 probe/materialize 结果模型。
  - `src/stata_agent/providers/csmar/client.py`：收口为 MCP-only 适配器；删除 SDK/catalog 语义路径；返回类型改为显式模型，避免裸 `dict` 边界泄漏。
  - `src/stata_agent/providers/csmar/catalog.py`：已删除（不再保留 provider 内语义评分/别名字典）。
  - 新增 `src/stata_agent/providers/csmar/contracts.py`、`normalizers.py`：承载 MCP payload 契约与归一化逻辑，降低单文件复杂度。
  - `src/stata_agent/services/variable_mapper.py` + 新增 `mapping_candidate_builder.py`：实现“表发现→schema判别→可选search_fields复核”的预算受控流程；judge 异常/拒绝时启发式 fallback。
  - `tests/live_api_support.py`：live provider 切换为 `CsmarBridgeClient.from_settings`，不再依赖本地 `csmarapi` 可导入检查。
- 测试改造：
  - `tests/s1_feasibility/test_t4_variable_mapper.py` 拆分为 `test_t4_variable_mapper_core.py`、`test_t4_variable_mapper_budget.py`、`test_t4_variable_mapper_live.py` 与 `t4_variable_mapper_support.py`，覆盖预算上限、辅助检索复核、Hard fail-fast、Soft gap。
  - `tests/s1_feasibility/test_csmar_bridge_mcp_adapter.py` 更新为显式 MCP 元数据能力断言。
  - `tests/s1_feasibility/test_t5_probe_executor.py` fake provider 同步新端口。
- 验证结果：
  - `uv run pytest tests/s1_feasibility -q` ✅（20 passed, 8 skipped）
  - `uv run python -m pyright` ✅（0 errors）
  - `uv run python -m tools.harness lint` ✅
  - `uv run python -m tools.run_quality_gates` ⚠️：仅 `ruff check .` 失败，集中在 `docs/references/csmarapi/**` 历史参考代码；其余门禁（pyright/import-linter/architecture/harness）通过。
- 当前阶段：S1 已交付后的回炉增强继续推进；`feature_list.json` 未改动，S2 排序不变。
- 分支：main

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23

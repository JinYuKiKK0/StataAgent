# 双仓 MCP 重构代码审查问题清单（S1 范围）

> 说明：
> - 本清单基于并行 9 个 CR 任务的只读审查结果汇总。
> - 按你的范围约束，`StataAgent` 当前仅实现 `S1 -> gateway_approval`，`S2/S3` 占位不作为缺陷。
> - 每条问题均包含：**问题、位置、影响、可能修复方案**。

---

## P0（阻断/高优先）

### 1) [Blocker] Provider 失败审计不全（仅捕获 `CsmarMetadataError`）
- **问题**：`tool_call` 仅捕获 `CsmarMetadataError`；`timeout/runtime` 等异常可能直接冒泡，失败调用无 trace。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/src/stata_agent/providers/csmar/tool_call.py`
	- `/home/jinyu/PythonProject/StataAgent/src/stata_agent/providers/csmar/mcp_transport.py`
- **影响**：无法保证“成功/失败均可审计”，关键故障排查链断裂。
- **可能修复方案**：
	- 在 `call_mcp_tool_with_trace` 增加兜底 `except Exception`，先落 trace 再抛出；
	- 或在 transport 层将运行时异常统一归一化为 `CsmarMetadataError`。

### 2) [High] 配置错误被吞掉，存在“静默未配置”风险
- **问题**：`from_settings()` 吞掉 `build_csmar_mcp_launch_spec()` 的 `ValueError` 并继续运行，延迟到首次调用才暴露。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/src/stata_agent/providers/csmar/client.py`
	- `/home/jinyu/PythonProject/StataAgent/src/stata_agent/providers/csmar/mcp_runtime.py`
- **影响**：启动阶段看似正常，运行期才失败，且根因信息弱化。
- **可能修复方案**：
	- Provider 初始化改为 fail-fast；
	- 或保留原始配置异常并在启动健康检查阶段显式抛出。

### 3) [High] `materialize_query` 缺少冷却前置拦截
- **问题**：`probe_query` 有冷却前置检查，`materialize_query` 缺少对等前置检查。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/services/query.py`
- **影响**：冷却窗口内可能继续触发上游打包请求，增加限流与失败概率。
- **可能修复方案**：
	- 在 materialize 入口加入冷却门禁：命中时优先返回缓存，否则标准化 `rate_limited`。

### 4) [High] `rate_limited` 后仍循环重试，可能放大限流
- **问题**：materialize 在命中 `rate_limited` 后仍继续循环重试。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/services/query.py`
- **影响**：单次调用内重复打上游，放大限流与失败风暴风险。
- **可能修复方案**：
	- 对 `rate_limited` 直接 fail-fast 返回（附 `retry_after_seconds`），不进入后续重试。

### 5) [High] 兜底异常路径审计不闭环
- **问题**：`tool_error_boundary` 兜底后返回错误，但非业务异常不保证审计落库。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/presenters.py`
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/server.py`
- **影响**：异常可见但不可对账，审计完整性不足。
- **可能修复方案**：
	- 在兜底边界补最小审计写入（tool/request/error/timestamp）；
	- `_safe_log_trace` 失败时增加可观测降级日志。

### 6) [High] 跨仓 `materialize` 结果契约漂移
- **问题**：StataAgent 侧仍偏旧 `validation_id/output_dir/files` 语义；MCP 侧已是 `download_id/query_fingerprint/...`。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/src/stata_agent/domains/mapping/types.py`
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/models.py`
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/core/types.py`
- **影响**：调用方对 materialize 回执语义理解不一致，易触发兼容问题。
- **可能修复方案**：
	- 统一 StataAgent DTO 到 MCP 当前对外契约，消除旧字段依赖。

### 7) [High] 存在旁路脚本，破坏“仅 MCP 边界”认知
- **问题**：保留可执行直连脚本，绕过 MCP 标准边界。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/test_csmar_raw.py`
- **影响**：形成软双轨，增加误用概率与维护噪声。
- **可能修复方案**：
	- 删除；或迁移到 `tools/debug` 且重命名为非 `test_`，并加“非生产路径”声明。

---

## P1（中优先）

### 8) [Medium] 冷却键策略割裂（probe 与 materialize 不统一）
- **问题**：probe 侧与 materialize 侧使用不同冷却键路径，策略一致性不足。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/services/query.py`
- **影响**：维护复杂度上升，边界行为难预测。
- **可能修复方案**：
	- 统一冷却键语义并在 probe/materialize 全路径对齐。

### 9) [Medium] `cache_key` 对列顺序敏感，语义等价查询可能失配
- **问题**：等价列集合不同顺序会形成不同键。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/services/query.py`
- **影响**：缓存命中下降，冷却绕过概率上升。
- **可能修复方案**：
	- 若业务允许顺序无关，对 `columns` 做去重排序后再构建 key。

### 10) [Medium] `query_specs` 只写不读
- **问题**：状态写入存在但无读取闭环。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/services/query.py`
- **影响**：状态语义漂移，长期形成冗余与误导。
- **可能修复方案**：
	- 二选一：补读取恢复闭环；或删除写入以简化状态模型。

### 11) [Medium] Gateway 摘要缺 `validation_id`
- **问题**：trace 摘要未携带 `validation_id`，链路可追溯性不完整。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/src/stata_agent/workflow/graph.py`
- **影响**：人工审阅与问题追踪时缺关键锚点。
- **可能修复方案**：
	- 在 `probe_trace_summary` 增加 `validation_id` 字段并补测试断言。

### 12) [Medium] trace 去重策略可能丢失更完整记录
- **问题**：当前按 `trace_id` first-win，后续更完整记录可能被覆盖丢弃。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/src/stata_agent/workflow/stages/phase1_feasibility.py`
- **影响**：审计信息完整性下降。
- **可能修复方案**：
	- 改为“信息更丰富优先”合并，或字段级 merge。

### 13) [Medium] `search_fields` scope 兜底偏强，存在召回回流风险
- **问题**：字段不命中时可被 table/database scope 相似度兜底命中。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/services/metadata.py`
- **影响**：边界从“字段确定性检索”滑向范围召回，噪声变大。
- **可能修复方案**：
	- 引入严格字段模式（默认严格）；scope 匹配改为显式开关或提高阈值。

### 14) [Medium] `_safe_log_trace` 失败静默吞掉
- **问题**：审计写入失败缺少可观测信号。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/server.py`
- **影响**：可能出现“以为已审计，实际未落库”的盲区。
- **可能修复方案**：
	- 增加最小告警输出或计数器。

### 15) [Medium] `InMemoryState` 兼容别名仍导出
- **问题**：别名与真实实现（SQLite 持久化）不一致，制造双实现错觉。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/infra/state.py`
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/csmar_mcp/infra/__init__.py`
- **影响**：软双轨认知与误用风险。
- **可能修复方案**：
	- 移除别名与导出，仅保留 `PersistentState`。

### 16) [Medium] 文档与仓库现状不一致
- **问题**：`AGENTS.md` 引用不存在的 `PLAN.md`，且测试现状描述过时。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/AGENTS.md`
- **影响**：审查基线歧义，团队协作信息噪声。
- **可能修复方案**：
	- 修正引用与测试说明，保持文档与仓库一致。

---

## P2（测试与收口）

### 17) [Coverage] fail-fast 错误码覆盖不足
- **问题**：`table_not_found/field_not_found` 专项断言不充分。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/tests/s1_feasibility/test_t5_probe_executor.py`
- **影响**：未来回退到弱错误契约时不易被测试阻断。
- **可能修复方案**：
	- 补参数化用例，分别断言 `error_code/retry_after_seconds/fail-fast warning`。

### 18) [Coverage] “不内部重试”缺强断言
- **问题**：错误场景下缺调用次数约束。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/tests/s1_feasibility/test_t5_probe_executor.py`
- **影响**：若误引入重试，测试可能不报警。
- **可能修复方案**：
	- 在失败场景显式断言 provider 调用次数 `== 1`。

### 19) [Coverage] 预算“按变量重置”未显式锁定
- **问题**：现有预算测试更偏单变量路径。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/tests/s1_feasibility/test_t4_variable_mapper_budget.py`
- **影响**：多变量情况下预算污染风险难以提前发现。
- **可能修复方案**：
	- 增加多变量测试，断言每变量独立执行预算。

### 20) [Coverage] MCP 服务端契约层测试不足
- **问题**：当前测试偏 service/state，server/presenters/models 关键契约覆盖不足。
- **位置**：
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/tests/test_services.py`
	- `/home/jinyu/PythonProject/CSMAR-Data-MCP/tests/test_runtime.py`
- **影响**：工具层参数校验、错误整形、审计落库等回归风险高。
- **可能修复方案**：
	- 新增 server/presenters/models 维度回归测试（含失败路径）。

### 21) [Coverage] 高层编排回归偏 live_api，默认环境可能“跳过即绿色”
- **问题**：部分关键链路测试依赖 live 标记，CI 默认可能跳过。
- **位置**：
	- `/home/jinyu/PythonProject/StataAgent/tests/core_workflow/test_workflow_orchestrator.py`
	- `/home/jinyu/PythonProject/StataAgent/tests/entrypoints/test_agent_graph.py`
- **影响**：非 live 环境下覆盖不足，回归漏检概率上升。
- **可能修复方案**：
	- 增补非 live 的最小编排回归测试基线。

---

## 建议修复批次

- **批次 1（阻断）**：1~7
- **批次 2（一致性）**：8~16
- **批次 3（护栏）**：17~21


# CSMAR 全量 MCP 化重构方案

## Summary
- 建议采用 `MCP 作为唯一 CSMAR 集成边界 + StataAgent 服务层受控调用`，不把 CSMAR 工具直接交给主模型自由调用。
- 你补充的约束现在明确纳入方案：`CSMAR-MCP` 不负责语义别名扩展，不保留 `_SEMANTIC_QUERY_ALIASES` 这类硬编码知识。MCP 只返回确定性的数据库、表、字段、schema 和 probe 结果；字段语义判断、别名理解、最终映射决策全部由 `StataAgent` 完成。
- 当前故障的根因仍是边界设计错误：provider 同时承担 SDK 访问、catalog 爬取、候选搜索、语义猜测、probe 调用，而状态里又没有保存真实请求参数。全面 MCP 化的目标不是“换个壳”，而是把职责拆清、调用收敛、审计补齐。

## Implementation Changes
### 1. 明确 MCP 的职责下限：确定性，不做语义决策
- 删除 `CSMAR-Data-MCP/csmar_mcp/services/metadata.py` 中 `_SEMANTIC_QUERY_ALIASES` 及其派生逻辑。
- `csmar_search_fields` 保留，但降级为确定性字段检索工具：
  - 只允许基于 `field_name`、`field_label`、`field_description`、`table_code`、`table_name`、`database_name` 做字面/相似度检索。
  - 不做同义词展开、不做经济学语义猜测、不做“ROA -> ROAA”这类领域推断。
- `csmar_get_table_schema` 成为字段判断的主入口。Agent/服务层应先缩小到候选表，再拉 schema，自行在字段集合上做语义判别。
- MCP 返回结果必须区分：
  - 查询标识：`database_name`、`table_code`、`field_name`
  - 展示信息：`table_name`、`field_label`、`field_description`
- MCP 不保存任何领域别名字典；如果未来需要标签增强，只允许来自上游 schema 原始元数据，不允许本地硬编码经济学知识。

### 2. MCP 先补成可当“唯一边界”的能力
- 保持 `CSMAR-Data-MCP` 独立逻辑，按你选定的 monorepo 方式纳入开发，但 `StataAgent` 只通过标准 `stdio MCP` 调用，禁止直接 import `csmar_mcp`。
- 把 MCP 的运行时状态从 `InMemoryState` 升级为 `SQLite` 持久化状态，默认落在 `WORKSPACE_DIR/.stata_agent/csmar_mcp/`。持久化内容固定为：metadata cache、probe cache、validation registry、rate-limit cooldown、tool audit log。
- 重写字段发现流程，禁止无界扫描全部表字段：
  1. `search_tables` 先把范围收敛到最多 `5` 个候选表
  2. `get_table_schema` 读取这些候选表的 schema
  3. 由调用侧在 schema 上完成语义映射
- 所有 MCP 工具结果都必须有稳定错误契约：`code/message/hint/retry_after_seconds/suggested_args_patch`，并把 `upstream_code/raw_message` 写入审计日志。
- `csmar_probe_query` 继续返回 `validation_id` 和 `query_fingerprint`；`csmar_materialize_query` 只接受 `validation_id`。长期恢复依赖 `query_fingerprint + query spec`，不依赖过期的 `validation_id`。

### 3. StataAgent 用 MCP adapter 替换现有 CSMAR provider
- 保留 `src/stata_agent/providers/csmar/` 包路径，内部实现改成 `MCP stdio transport + tool response normalizer + budget/cache guard`。
- 新 provider 只暴露受控能力：
  - `search_tables`
  - `get_table_schema`
  - `probe_query`
  - `materialize_query`
  - `list_databases/list_tables` 仅用于 repair
- `providers/settings.py` 迁移为 MCP 启动配置：
  - `CSMAR_MCP_COMMAND`
  - `CSMAR_MCP_ARGS`
  - `CSMAR_MCP_WORKDIR`
  - `CSMAR_MCP_START_TIMEOUT_SECONDS`
  - `CSMAR_MCP_CALL_TIMEOUT_SECONDS`
  - `CSMAR_MCP_STATE_DIR`
- `StataAgent` 运行时固定启动 sibling `CSMAR-Data-MCP` 进程；依赖方向固定为单向，禁止直接 import `csmarapi` 或 `csmar_mcp`。

### 4. 把语义映射完整回收到 StataAgent
- `VariableMapper` 改成显式两阶段：
  1. `表发现`：根据变量名、研究主题、样本范围调用 `search_tables`
  2. `字段判别`：对候选表调用 `get_table_schema`，由 `TongyiVariableSemanticJudge + 启发式规则` 在 schema 内做最终字段映射
- `csmar_search_fields` 不再作为主映射入口，只能作为可选辅助检索；即使使用，也只提供字面候选，最终决策仍必须基于真实 schema。
- `VariableMapper` 每个变量的固定预算：
  - 最多 `1` 次 `search_tables`
  - 最多 `2` 次 `get_table_schema`
  - 可选 `1` 次 `search_fields` 作为辅助，但默认不依赖它
- 语义别名、同义词、经济学常识全部留在 `StataAgent`：
  - LLM 判别提示词
  - 本地启发式 fallback
  - 用户可审计的 mapping evidence
- 不允许把领域词典重新塞回 MCP；MCP 的目标是“真实元数据服务”，不是“知识推理器”。

### 5. 统一稳定契约，先修正“表标识”问题
- 把所有跨边界类型里的 `table_name` 改成 `table_code` 作为唯一查询标识；展示名单独保留 `table_name`。
- 同步调整以下稳定契约：
  - `CsmarFieldCandidate`
  - `CsmarFieldProbeRequest/Result`
  - `VariableBinding`
  - `QueryPlan`
  - `VariableProbeResult`
- `csmar_database` 统一改名为 `database_name`。
- 新增可序列化审计类型 `CsmarToolTrace`，字段固定为：`trace_id/tool_name/request_payload/result_summary/error/query_fingerprint/validation_id/cached/started_at/completed_at`。
- `ResearchState` 新增 `csmar_traces`；`VariableBinding` 和 `VariableProbeResult` 只保存相关 `trace_id`。

### 6. S1 和 S3 的执行边界
- `_map_variables_node` 不再触发全量 catalog crawl，也不再依赖 provider 内置 alias 词典。
- `ProbeExecutor` 改为调用 `csmar_probe_query`，一条 binding 只 probe 一次；`table_not_found/field_not_found/rate_limited` 不允许内部循环重试。
- Gateway 前的数据契约必须附带：`mapping evidence + trace_id + query_fingerprint + residual risk`。
- `S3-T1 QueryPlan` 直接产出 MCP-ready query spec：`table_code/columns/condition/start_date/end_date/expected_grain`。
- `S3-T2` 固定流程为 `probe_query -> materialize_query`；`S3-T3/S3-T4` 只消费本地工件，不再回调 CSMAR。
- legacy `catalog.py` 和 `CsmarBridgeClient.fetch()` stub 在切换完成后删除，不长期双栈维护。

## Public API And Type Changes
- `VariableBinding.table_name -> table_code`
- `VariableBinding` 新增展示字段 `table_name`
- `QueryPlan.table_name -> table_code`
- `CsmarFieldProbeRequest.table_name -> table_code`
- `ResearchState` 新增 `csmar_traces: list[CsmarToolTrace]`
- `ProbeCoverageResult` / `VariableProbeResult` 新增 `trace_id`
- `Settings` 从直接 SDK 凭证迁移到 MCP 启动配置
- `CSMAR-MCP` 不再暴露任何基于硬编码别名的“语义搜索保证”；所有搜索结果语义仅代表字面匹配候选

## Test Plan
- MCP 单测：
  - `_SEMANTIC_QUERY_ALIASES` 已删除
  - `search_fields` 不做同义词扩展，只做确定性检索
  - `search_tables -> get_table_schema` 可支撑字段判别流程
  - `table_code/table_name` 不混淆
  - 持久化 cache/cooldown 跨进程生效
- StataAgent 单测：
  - `VariableMapper` 基于 schema 而不是 MCP alias 做映射
  - LLM/启发式能在同一表字段列表中判别 `ROA`、`资本充足率` 等变量
  - 每变量调用预算与去重生效
  - `ProbeExecutor` 对 `table_not_found`、`field_not_found`、`rate_limited` fail-fast
  - `ResearchState.csmar_traces` 正确记录请求参数和结果摘要
- 集成测试：
  - fake/recorded MCP server 跑完整 `S1 映射 -> probe -> data contract`
  - 专门覆盖“字段语义由 Agent 判断，不依赖 MCP 硬编码 alias”的回归场景
  - 覆盖“相同失败 probe 不会重复调用上游”
- Live smoke：
  - 仅保留一条真实链路，验证 `search_tables/get_table_schema/probe_query` 可用
  - 主测试集不再依赖本地 `csmarapi`

## Assumptions
- `csmar_search_fields` 保留为确定性辅助检索工具，不删除；但主映射路径默认走 `search_tables + get_table_schema + Agent 判别`。
- 领域语义、同义词和最终字段映射全部属于 `StataAgent`，不属于 `CSMAR-MCP`。
- monorepo 只解决版本协同，不改变边界纪律；`StataAgent` 与 `CSMAR-Data-MCP` 的唯一合法交互仍是标准 MCP `stdio`。
- 实施顺序固定为：先删 MCP 语义 alias 并补持久化状态，再替换 StataAgent provider 与 S1，最后切 S3 并删除 legacy SDK 实现。

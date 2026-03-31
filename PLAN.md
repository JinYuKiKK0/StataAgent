# CSMAR MCP 原生工具化重构草案

## Summary
- 结论：按“当前代码最小可运行”看，现有 `csmar-MCP` 只够覆盖一部分 S1 探针底层动作；按“项目真实目标”看，它还不满足 Agent 对 CSMAR 的完整交互需求。
- 现状差异：当前 [providers/csmar.py](d:/Developments/PythonProject/StataAgent/src/stata_agent/providers/csmar.py) 实际依赖的是 `字段候选发现 + 字段存在性 + queryCount`，其中“字段候选发现”现在还是本地硬编码 catalog，不是 MCP 提供的能力。
- 实测结论：`csmar_catalog_search` 对 `ROA`、`资本充足率` 这类字段语义查询返回空，只有表名/表码能稳定命中；`csmar_get_table_schema(..., field_query=...)` 只有在表已知时才有用；`csmar_query_validate` 能返回 `row_count` 和 `field_not_found`，但 `query_validate -> download_materialize` 没有形成可靠链路，实测 `can_download: true` 仍可能接 `upstream_error`。
- 运行时方向：保持 LangGraph 为顶层编排；在运行时引入 `langchain-mcp-adapters` 的 `MultiServerMCPClient`，把 CSMAR 暴露成 LangChain/LangGraph 工具，而不是继续把 SDK 方法包成 provider。参考 LangChain 官方 MCP 文档：https://docs.langchain.com/oss/python/langchain/mcp

## 需要补充的 MCP 接口
- 新增 `csmar_search_fields`：输入自然语言变量名、可选数据库/表范围；输出字段级候选，而不是表级候选。返回至少包含 `database_name`、`table_code`、`table_name`、`field_name`、`field_label`、`field_description`、`data_type`、`frequency_tags`、`role_tags`、`why_matched`。
- 升级 `csmar_get_table_schema`：不要只返回字段名字符串列表，应返回结构化字段对象；`field_query` 必须同时搜 `field_name + label + description`，否则 S1-T4 无法做语义映射。
- 升级 `csmar_query_validate`：返回 `validation_id`、`row_count`、`sample_rows`、`invalid_columns`、`retriable`、`vendor_message`、`recommended_chunks`，让它真正成为“探针/下载前校验”的稳定契约。
- 重做下载链路：推荐拆成 `csmar_start_download(validation_id|query_spec)`、`csmar_get_download_status(download_id)`、`csmar_materialize_download(download_id, output_dir)`；如果坚持单接口，就让 `csmar_download_materialize` 明确消费 `validation_id`，并返回完整 manifest。
- 统一错误契约：所有接口都返回结构化错误字段 `code`、`message`、`vendor_message`、`retriable`、`scope`、`query_fingerprint`，不要只给泛化的 `upstream_error`。

## StataAgent 重构
- 把 [providers/csmar.py](d:/Developments/PythonProject/StataAgent/src/stata_agent/providers/csmar.py) 改成 MCP client/bootstrap 层，只负责 transport、auth、session、tool load；不再承载字段匹配和探针业务逻辑。这样仍符合 [ARCHITECTURE.md](d:/Developments/PythonProject/StataAgent/ARCHITECTURE.md) 里“外部集成只能在 providers” 的约束。
- 在 [pyproject.toml](d:/Developments/PythonProject/StataAgent/pyproject.toml) 增加 `langchain-mcp-adapters`，并在 [workflow/orchestrator.py](d:/Developments/PythonProject/StataAgent/src/stata_agent/workflow/orchestrator.py) 构造 CSMAR MCP client/toolset，而不是实例化 `CsmarBridgeClient`。
- 重写 [domains/mapping/ports.py](d:/Developments/PythonProject/StataAgent/src/stata_agent/domains/mapping/ports.py) 一类 SDK 形状接口，改成稳定的 MCP 归一化结果类型，例如 `CsmarFieldMatch`、`CsmarProbeResult`、`CsmarValidationResult`、`CsmarDownloadManifest`。
- 保留 [workflow/stages/phase1_feasibility.py](d:/Developments/PythonProject/StataAgent/src/stata_agent/workflow/stages/phase1_feasibility.py) 的阶段顺序不变，但替换节点内部实现：变量映射改为“LLM + MCP 字段发现”，探针执行改为“结构化 validate/probe”，数据契约改为记录字段匹配证据、query fingerprint 和 residual risks。
- 提前按未来链路改 S3：`S3-T1` 的 QueryPlan 改为 MCP-ready query spec；`S3-T2` 改为消费 `validation_id/download_id` 并产出 `DownloadManifest`；`S3-T3/S3-T4` 只读取本地物化工件，不再回调 CSMAR。
- 从 [providers/settings.py](d:/Developments/PythonProject/StataAgent/src/stata_agent/providers/settings.py) 移除 `CSMAR_ACCOUNT/CSMAR_PASSWORD/CSMAR_LANGUAGE` 的应用侧依赖；如果运行时仍需连接信息，只保留 MCP transport/url/header 级配置。

## Test Plan
- 用 MCP fixture 替换 [tests/live_api_support.py](d:/Developments/PythonProject/StataAgent/tests/live_api_support.py) 里的 `csmarapi` 依赖，测试边界改成“能否调用 MCP 并正确归一化结果”。
- 增加 MCP 契约测试：字段搜索、schema 过滤、invalid field、probe/validate、download lifecycle、结构化错误翻译。
- 增加一个基于 fake/recorded MCP server 的 S1 工作流集成测试，覆盖“变量映射 -> 探针 -> Gateway 前数据契约”。
- live smoke 只保留最小兼容性校验，不再让主回归测试依赖真实 CSMAR。

## Assumptions
- 本草案按你选定的 `原生工具化` 路径设计，不走“provider 内部偷偷换实现”的兼容方案。
- 缺口优先补进 `csmar-MCP`，不把字段别名、下载状态机、供应商冷却规避重新塞回 Agent 本地。
- 在 `csmar_search_fields` 或等价字段级发现接口落地前，不应删除当前本地 alias/catalog fallback。

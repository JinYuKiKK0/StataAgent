"""CSMAR Bridge MCP 适配行为测试。"""

from pathlib import Path

from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest
from stata_agent.domains.mapping.types import CsmarTableSearchRequest
from stata_agent.providers.csmar.client import CsmarBridgeClient
from stata_agent.providers.csmar.contracts import McpToolPayload
from stata_agent.providers.csmar.errors import CsmarMetadataError
from stata_agent.providers.csmar.mcp_runtime import CsmarMcpLaunchSpec


class _FakeMcpToolCaller:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def call_tool(self, tool_name: str, arguments: dict[str, object]) -> McpToolPayload:
        self.calls.append((tool_name, arguments))
        if tool_name == "csmar_search_tables":
            return McpToolPayload(content={
                "items": [
                    {
                        "table_code": "BANK_Index",
                        "table_name": "银行指标",
                        "database_name": "银行财务",
                        "score": 0.98,
                        "why_matched": "contains query",
                    }
                ]
            })
        if tool_name == "csmar_get_table_schema":
            return McpToolPayload(content={
                "table_code": "BANK_Index",
                "table_name": "银行指标",
                "database_name": "银行财务",
                "fields": [
                    {
                        "field_name": "ROAA",
                        "field_label": "总资产收益率",
                        "field_description": "资产收益率指标",
                        "frequency_tags": ["annual"],
                    },
                    {
                        "field_name": "CapitalRatio",
                        "field_label": "资本充足率",
                        "field_description": "资本充足率指标",
                        "frequency_tags": ["annual"],
                    },
                ],
            })
        if tool_name == "csmar_search_fields":
            return McpToolPayload(content={
                "items": [
                    {
                        "table_code": "BANK_Index",
                        "table_name": "银行指标",
                        "database_name": "银行财务",
                        "field_name": "ROAA",
                        "field_label": "总资产收益率",
                        "field_description": "资产收益率指标",
                        "score": 0.93,
                        "why_matched": "label_contains_query",
                        "frequency_tags": ["annual"],
                    }
                ]
            })
        if tool_name == "csmar_probe_query":
            return McpToolPayload(content={
                "validation_id": "validation_test001",
                "query_fingerprint": "probe_hash_001",
                "row_count": 128,
                "can_materialize": True,
                "invalid_columns": [],
            })
        raise AssertionError(f"unexpected tool call: {tool_name}")


class _FailingProbeToolCaller(_FakeMcpToolCaller):
    def call_tool(self, tool_name: str, arguments: dict[str, object]) -> McpToolPayload:
        if tool_name == "csmar_probe_query":
            raise CsmarMetadataError(
                "probe 限流",
                code="rate_limited",
                retriable=True,
                vendor_message="retry later",
            )
        return super().call_tool(tool_name, arguments)


def _dummy_launch_spec() -> CsmarMcpLaunchSpec:
    return CsmarMcpLaunchSpec(
        command="uv",
        args=("run", "csmar-mcp", "--account", "a", "--password", "b"),
        cwd=Path("/tmp/CSMAR-Data-MCP"),
        start_timeout_seconds=20,
        call_timeout_seconds=120,
        env_overrides={},
    )


def test_search_tables_then_schema_via_mcp() -> None:
    """验证 MCP 适配层可显式执行 search_tables 与 get_table_schema。"""
    tool_caller = _FakeMcpToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    tables = client.search_tables(CsmarTableSearchRequest(query="ROA", limit=3))
    schema = client.get_table_schema("BANK_Index")

    assert tables
    assert tables[0].table_code == "BANK_Index"
    assert schema.table_code == "BANK_Index"
    assert schema.fields
    assert any(name == "csmar_search_tables" for name, _ in tool_caller.calls)
    assert any(name == "csmar_get_table_schema" for name, _ in tool_caller.calls)


def test_search_fields_returns_structured_hits() -> None:
    """验证 search_fields 作为辅助能力返回结构化字段命中。"""
    tool_caller = _FakeMcpToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    hits = client.search_fields(
        CsmarFieldSearchRequest(query="ROA", frequency_hint="annual", limit=5)
    )

    assert hits
    assert hits[0].table_code == "BANK_Index"
    assert hits[0].field_name == "ROAA"
    assert any(name == "csmar_search_fields" for name, _ in tool_caller.calls)


def test_probe_field_availability_uses_mcp_probe_result() -> None:
    """验证 MCP 分支会把 probe_query 结果映射为结构化可用性摘要。"""
    tool_caller = _FakeMcpToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    result = client.probe_field_availability(
        CsmarFieldProbeRequest(
            variable_name="ROA",
            table_code="BANK_Index",
            field_name="ROAA",
            contract_tier="hard",
            entity_scope="A股上市银行",
            analysis_grain="bank-year",
            time_start_year=2018,
            time_end_year=2023,
        )
    )

    assert result.field_exists is True
    assert result.table_code == "BANK_Index"
    assert result.row_count == 128
    assert result.query_fingerprint == "probe_hash_001"


def test_probe_field_availability_surfaces_mcp_rate_limit_error() -> None:
    """验证 MCP probe 抛限流错误时会被转换为可审计的失败结果。"""
    tool_caller = _FailingProbeToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    result = client.probe_field_availability(
        CsmarFieldProbeRequest(
            variable_name="ROA",
            table_code="BANK_Index",
            field_name="ROAA",
            contract_tier="hard",
            entity_scope="A股上市银行",
            analysis_grain="bank-year",
            time_start_year=2018,
            time_end_year=2023,
        )
    )

    assert result.field_exists is False
    assert result.table_code == "BANK_Index"
    assert result.retriable is True
    assert result.vendor_message == "retry later"


def test_client_drains_local_tool_traces() -> None:
    """验证 MCP 调用后可从 provider 侧拉取本地 trace 审计记录。"""
    tool_caller = _FakeMcpToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    client.search_tables(CsmarTableSearchRequest(query="ROA", limit=3))
    client.get_table_schema("BANK_Index")
    traces = client.drain_tool_traces()

    assert len(traces) == 2
    assert traces[0].trace_id
    assert traces[0].tool_name == "csmar_search_tables"
    assert traces[1].tool_name == "csmar_get_table_schema"

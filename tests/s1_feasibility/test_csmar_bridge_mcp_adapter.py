"""CSMAR Bridge MCP 适配行为测试。"""

from pathlib import Path

import pytest

from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.providers.csmar.client import CsmarBridgeClient
from stata_agent.providers.csmar.contracts import McpToolPayload
from stata_agent.providers.csmar.errors import CsmarMetadataError
from stata_agent.providers.csmar.mcp_runtime import CsmarMcpLaunchSpec
from stata_agent.providers.settings import Settings


class _FakeMcpToolCaller:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def call_tool(self, tool_name: str, arguments: dict[str, object]) -> McpToolPayload:
        self.calls.append((tool_name, arguments))
        if tool_name == "csmar_list_databases":
            return McpToolPayload(content={"databases": ["银行财务", "财务报表"]})
        if tool_name == "csmar_list_tables":
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


class _RuntimeFailingToolCaller(_FakeMcpToolCaller):
    def call_tool(self, tool_name: str, arguments: dict[str, object]) -> McpToolPayload:
        if tool_name == "csmar_list_tables":
            raise TimeoutError("MCP tool call timed out")
        return super().call_tool(tool_name, arguments)


class _MaterializeToolCaller(_FakeMcpToolCaller):
    def call_tool(self, tool_name: str, arguments: dict[str, object]) -> McpToolPayload:
        if tool_name == "csmar_materialize_query":
            return McpToolPayload(
                content={
                    "download_id": "download_test001",
                    "query_fingerprint": "probe_hash_001",
                    "output_dir": "/tmp/csmar-output",
                    "files": ["/tmp/csmar-output/a.csv", "/tmp/csmar-output/b.csv"],
                    "row_count": 128,
                    "archive_path": "/tmp/csmar-output/download_test001.zip",
                    "audit": {
                        "retries": 1,
                        "packaged_at": "2026-04-04T10:00:00Z",
                        "completed_at": "2026-04-04T10:01:00Z",
                    },
                }
            )
        return super().call_tool(tool_name, arguments)


class _MaterializeMissingFieldsToolCaller(_FakeMcpToolCaller):
    def call_tool(self, tool_name: str, arguments: dict[str, object]) -> McpToolPayload:
        if tool_name == "csmar_materialize_query":
            return McpToolPayload(content={"files": ["/tmp/csmar-output/a.csv"]})
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


def _build_settings(**overrides: object) -> Settings:
    payload: dict[str, object] = {
        "workspace_dir": Path("/tmp/stata-workspace"),
        "dashscope_api_key": "test-dashscope-key",
        "tongyi_model": "qwen-plus",
        "csmar_account": "demo-account",
        "csmar_password": "demo-password",
    }
    payload.update(overrides)
    return Settings.model_validate(payload)


def test_list_tables_then_schema_via_mcp() -> None:
    """验证 MCP 适配层会沿 list_databases/list_tables/schema 路径返回结构化元数据。"""
    tool_caller = _FakeMcpToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    databases = client.list_databases()
    tables = client.list_tables("银行财务")
    schema = client.get_table_schema("BANK_Index")

    assert databases == ["银行财务", "财务报表"]
    assert tables
    assert tables[0].table_code == "BANK_Index"
    assert schema.table_code == "BANK_Index"
    assert schema.fields
    assert any(name == "csmar_list_databases" for name, _ in tool_caller.calls)
    assert any(name == "csmar_list_tables" for name, _ in tool_caller.calls)
    assert any(name == "csmar_get_table_schema" for name, _ in tool_caller.calls)


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
    assert result.validation_id == "validation_test001"


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
    assert result.error_code == "rate_limited"
    assert result.retriable is True
    assert result.vendor_message == "retry later"
    traces = client.drain_tool_traces()
    assert len(traces) == 1
    assert traces[0].tool_name == "csmar_probe_query"
    assert traces[0].error is not None
    assert traces[0].error.get("code") == "rate_limited"


def test_client_drains_local_tool_traces() -> None:
    """验证 MCP 调用后可从 provider 侧拉取本地 trace 审计记录。"""
    tool_caller = _FakeMcpToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    client.list_tables("银行财务")
    client.get_table_schema("BANK_Index")
    traces = client.drain_tool_traces()

    assert len(traces) == 2
    assert traces[0].trace_id
    assert traces[0].tool_name == "csmar_list_tables"
    assert traces[1].tool_name == "csmar_get_table_schema"


def test_from_settings_fails_fast_when_credentials_missing() -> None:
    """验证 from_settings 在缺少凭证时直接失败，不延迟到运行期。"""
    settings = _build_settings(csmar_account=None, csmar_password=None)

    with pytest.raises(ValueError, match="CSMAR_ACCOUNT"):
        CsmarBridgeClient.from_settings(settings)


def test_runtime_exception_is_normalized_and_traced() -> None:
    """验证非业务异常会被归一化为 upstream_error 并写入本地 trace。"""
    tool_caller = _RuntimeFailingToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    with pytest.raises(CsmarMetadataError, match="MCP tool call timed out") as error:
        client.list_tables("银行财务")

    assert error.value.code == "upstream_error"
    traces = client.drain_tool_traces()
    assert len(traces) == 1
    assert traces[0].tool_name == "csmar_list_tables"
    assert traces[0].error is not None
    assert traces[0].error.get("code") == "upstream_error"
    assert traces[0].started_at
    assert traces[0].completed_at


def test_materialize_query_parses_new_contract_fields() -> None:
    """验证 materialize 返回会按 MCP 新契约解析。"""
    tool_caller = _MaterializeToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    result = client.materialize_query(
        validation_id="validation_test001",
        output_dir="/tmp/ignored-by-provider",
    )

    assert result.download_id == "download_test001"
    assert result.query_fingerprint == "probe_hash_001"
    assert result.output_dir == "/tmp/csmar-output"
    assert result.files == ["/tmp/csmar-output/a.csv", "/tmp/csmar-output/b.csv"]
    assert result.row_count == 128
    assert result.archive_path == "/tmp/csmar-output/download_test001.zip"
    assert result.audit.retries == 1

    traces = client.drain_tool_traces()
    assert len(traces) == 1
    assert traces[0].tool_name == "csmar_materialize_query"
    assert traces[0].validation_id == "validation_test001"


def test_materialize_query_rejects_missing_required_fields() -> None:
    """验证 materialize 响应缺少关键字段时会 fail-fast。"""
    tool_caller = _MaterializeMissingFieldsToolCaller()
    client = CsmarBridgeClient(
        mcp_launch_spec=_dummy_launch_spec(),
        mcp_tool_caller=tool_caller,
    )

    with pytest.raises(CsmarMetadataError, match="MCP materialize 返回缺少关键字段") as error:
        client.materialize_query(
            validation_id="validation_test001",
            output_dir="/tmp/ignored-by-provider",
        )

    assert error.value.code == "upstream_error"

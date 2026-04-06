# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from collections.abc import Mapping, Sequence

from stata_agent.providers.csmar.contracts import McpToolPayload
from stata_agent.providers.csmar.errors import CsmarMetadataError
from stata_agent.providers.csmar.mcp_runtime import CsmarMcpLaunchSpec
from stata_agent.providers.csmar.mcp_runtime import build_csmar_mcp_launch_spec
from stata_agent.providers.csmar.mcp_transport import CsmarMcpToolCaller
from stata_agent.providers.csmar.mcp_transport import StdioCsmarMcpToolCaller
from stata_agent.providers.csmar.materialize_parser import parse_materialize_payload
from stata_agent.providers.csmar.normalizers import build_query_condition
from stata_agent.providers.csmar.normalizers import extract_first_int
from stata_agent.providers.csmar.normalizers import normalize_object_rows
from stata_agent.providers.csmar.normalizers import normalize_tags
from stata_agent.providers.csmar.normalizers import probe_scope_warnings
from stata_agent.providers.csmar.tool_call import call_mcp_tool_with_trace
from stata_agent.providers.csmar.types import CsmarMaterializeQueryResult
from stata_agent.providers.csmar.types import CsmarProbeQueryResult
from stata_agent.providers.csmar.types import CsmarToolTrace
from stata_agent.providers.settings import Settings
from stata_agent.services.mapping.contracts import CsmarFieldProbeRequest
from stata_agent.services.mapping.contracts import CsmarFieldProbeResult
from stata_agent.services.mapping.contracts import CsmarSchemaField
from stata_agent.services.mapping.contracts import CsmarTableRecord
from stata_agent.services.mapping.contracts import CsmarTableSchema


class CsmarBridgeClient:
    def __init__(
        self,
        *,
        account: str | None = None,
        password: str | None = None,
        language: int = 0,
        mcp_launch_spec: CsmarMcpLaunchSpec | None = None,
        mcp_tool_caller: CsmarMcpToolCaller | None = None,
    ) -> None:
        self._account = (account or "").strip()
        self._password = (password or "").strip()
        self._language = language
        self._mcp_launch_spec = mcp_launch_spec
        self._mcp_tool_caller = mcp_tool_caller
        self._tool_traces: list[CsmarToolTrace] = []

    @classmethod
    def from_settings(cls, settings: Settings) -> "CsmarBridgeClient":
        password = (
            settings.csmar_password.get_secret_value()
            if settings.csmar_password is not None
            else None
        )
        mcp_launch_spec = build_csmar_mcp_launch_spec(settings)
        return cls(
            account=settings.csmar_account,
            password=password,
            language=settings.csmar_language,
            mcp_launch_spec=mcp_launch_spec,
        )

    @property
    def mcp_launch_spec(self) -> CsmarMcpLaunchSpec | None:
        return self._mcp_launch_spec

    def list_databases(self) -> list[str]:
        payload = self._call_mcp_tool("csmar_list_databases", {}).content
        databases = payload.get("databases")
        if not isinstance(databases, Sequence) or isinstance(
            databases, (str, bytes, bytearray)
        ):
            raise CsmarMetadataError("MCP 返回的数据库列表格式非法。", code="upstream_error")
        return [str(item) for item in databases if str(item).strip()]

    def list_tables(self, database_name: str) -> list[CsmarTableRecord]:
        payload = self._call_mcp_tool(
            "csmar_list_tables", {"database_name": database_name}
        ).content
        items = payload.get("items")
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
            raise CsmarMetadataError("MCP 返回的表列表格式非法。", code="upstream_error")
        normalized: list[CsmarTableRecord] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            table_code = str(item.get("table_code") or "").strip()
            table_name = str(item.get("table_name") or table_code).strip()
            if table_code:
                normalized.append(
                    CsmarTableRecord(
                        table_code=table_code,
                        table_name=table_name,
                        database_name=database_name,
                    )
                )
        return normalized

    def get_table_schema(self, table_code: str) -> CsmarTableSchema:
        payload = self._call_mcp_tool(
            "csmar_get_table_schema", {"table_code": table_code}
        ).content
        fields = payload.get("fields")
        if not isinstance(fields, Sequence) or isinstance(fields, (str, bytes, bytearray)):
            raise CsmarMetadataError("MCP 返回的 schema 格式非法。", code="upstream_error")

        normalized_fields: list[CsmarSchemaField] = []
        for field in fields:
            if not isinstance(field, Mapping):
                continue
            field_name = str(field.get("field_name") or "").strip()
            if not field_name:
                continue
            normalized_fields.append(
                CsmarSchemaField(
                    field_name=field_name,
                    field_label=str(field.get("field_label") or "").strip(),
                    field_description=str(field.get("field_description") or "").strip(),
                    data_type=str(field.get("data_type") or "").strip(),
                    frequency_tags=normalize_tags(field.get("frequency_tags")),
                    role_tags=normalize_tags(field.get("role_tags")),
                )
            )

        return CsmarTableSchema(
            table_code=str(payload.get("table_code") or table_code).strip(),
            table_name=str(payload.get("table_name") or table_code).strip(),
            database_name=str(payload.get("database_name") or "").strip(),
            fields=normalized_fields,
        )

    def probe_query(
        self,
        *,
        table_code: str,
        columns: list[str],
        condition: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        sample_rows: int = 0,
    ) -> CsmarProbeQueryResult:
        payload = self._call_mcp_tool(
            "csmar_probe_query",
            {
                "table_code": table_code,
                "columns": columns,
                "condition": condition,
                "start_date": start_date,
                "end_date": end_date,
                "sample_rows": max(0, min(sample_rows, 5)),
            },
        ).content
        if "validation_id" not in payload or "query_fingerprint" not in payload:
            raise CsmarMetadataError("MCP probe 返回缺少关键字段。", code="upstream_error")
        return CsmarProbeQueryResult(
            validation_id=str(payload.get("validation_id") or "").strip(),
            query_fingerprint=str(payload.get("query_fingerprint") or "").strip(),
            row_count=extract_first_int(payload.get("row_count")),
            invalid_columns=normalize_tags(payload.get("invalid_columns")),
            sample_rows=normalize_object_rows(payload.get("sample_rows")),
            can_materialize=bool(payload.get("can_materialize", True)),
        )

    def materialize_query(
        self, *, validation_id: str, output_dir: str
    ) -> CsmarMaterializeQueryResult:
        payload = self._call_mcp_tool(
            "csmar_materialize_query",
            {"validation_id": validation_id, "output_dir": output_dir},
        ).content
        return parse_materialize_payload(payload)

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        try:
            probe_payload = self.probe_query(
                table_code=request.table_code,
                columns=[request.field_name],
                condition=build_query_condition(request.field_name),
                start_date=f"{request.time_start_year}-01-01",
                end_date=f"{request.time_end_year}-12-31",
                sample_rows=0,
            )
        except CsmarMetadataError as exc:
            return CsmarFieldProbeResult(
                variable_name=request.variable_name,
                table_code=request.table_code,
                field_name=request.field_name,
                field_exists=False,
                query_fingerprint=f"{request.table_code}.{request.field_name}",
                validation_id="",
                scope_level="time_scoped",
                vendor_message=exc.vendor_message,
                error_code=exc.code,
                hint=exc.hint,
                retry_after_seconds=exc.retry_after_seconds,
                suggested_args_patch=exc.suggested_args_patch,
                retriable=exc.retriable,
                warnings=probe_scope_warnings(request.entity_scope),
            )

        field_exists = request.field_name not in probe_payload.invalid_columns
        row_count = probe_payload.row_count
        query_fingerprint = probe_payload.query_fingerprint.strip()
        if not query_fingerprint:
            query_fingerprint = f"{request.table_code}.{request.field_name}"

        return CsmarFieldProbeResult(
            variable_name=request.variable_name,
            table_code=request.table_code,
            field_name=request.field_name,
            field_exists=field_exists,
            row_count=row_count,
            query_fingerprint=query_fingerprint,
            validation_id=probe_payload.validation_id,
            scope_level="time_scoped",
            error_code="field_not_found" if not field_exists else "",
            hint=(
                "字段不存在，请先检查 schema 并修正字段代码。"
                if not field_exists
                else ""
            ),
            warnings=probe_scope_warnings(request.entity_scope),
        )

    def drain_tool_traces(self) -> list[CsmarToolTrace]:
        traces = list(self._tool_traces)
        self._tool_traces.clear()
        return traces

    def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpToolPayload:
        caller = self._get_mcp_tool_caller()
        sanitized_args = {k: v for k, v in arguments.items() if v is not None}
        return call_mcp_tool_with_trace(
            tool_name=tool_name,
            arguments=sanitized_args,
            caller=caller,
            tool_traces=self._tool_traces,
        )

    def _get_mcp_tool_caller(self) -> CsmarMcpToolCaller:
        if self._mcp_tool_caller is not None:
            return self._mcp_tool_caller
        if self._mcp_launch_spec is None:
            raise CsmarMetadataError(
                "MCP 启动配置缺失，无法调用 CSMAR MCP 工具。",
                code="mcp_unconfigured",
            )
        self._mcp_tool_caller = StdioCsmarMcpToolCaller(self._mcp_launch_spec)
        return self._mcp_tool_caller

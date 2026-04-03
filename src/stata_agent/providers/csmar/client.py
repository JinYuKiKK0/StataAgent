# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from stata_agent.domains.fetch.types import QueryPlan
from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarMaterializeQueryResult
from stata_agent.domains.mapping.types import CsmarFieldSearchHit
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest
from stata_agent.domains.mapping.types import CsmarProbeQueryResult
from stata_agent.domains.mapping.types import CsmarSchemaField
from stata_agent.domains.mapping.types import CsmarTableCandidate
from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import CsmarTableSearchRequest
from stata_agent.providers.csmar.contracts import McpToolPayload
from stata_agent.providers.csmar.errors import CsmarMetadataError
from stata_agent.providers.csmar.mcp_runtime import CsmarMcpLaunchSpec
from stata_agent.providers.csmar.mcp_runtime import build_csmar_mcp_launch_spec
from stata_agent.providers.csmar.mcp_transport import CsmarMcpToolCaller
from stata_agent.providers.csmar.mcp_transport import StdioCsmarMcpToolCaller
from stata_agent.providers.csmar.normalizers import build_query_condition
from stata_agent.providers.csmar.normalizers import extract_first_int
from stata_agent.providers.csmar.normalizers import normalize_object_rows
from stata_agent.providers.csmar.normalizers import normalize_tags
from stata_agent.providers.csmar.normalizers import probe_scope_warnings
from stata_agent.providers.settings import Settings


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

    @classmethod
    def from_settings(cls, settings: Settings) -> "CsmarBridgeClient":
        password = (
            settings.csmar_password.get_secret_value()
            if settings.csmar_password is not None
            else None
        )
        mcp_launch_spec: CsmarMcpLaunchSpec | None = None
        try:
            mcp_launch_spec = build_csmar_mcp_launch_spec(settings)
        except ValueError:
            # 保持与既有行为兼容：允许在运行期再报告凭证缺失。
            mcp_launch_spec = None
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

    def list_tables(self, database_name: str) -> list[dict[str, str]]:
        payload = self._call_mcp_tool(
            "csmar_list_tables", {"database_name": database_name}
        ).content
        items = payload.get("items")
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
            raise CsmarMetadataError("MCP 返回的表列表格式非法。", code="upstream_error")
        normalized: list[dict[str, str]] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            table_code = str(item.get("table_code") or "").strip()
            table_name = str(item.get("table_name") or table_code).strip()
            if table_code:
                normalized.append({"table_code": table_code, "table_name": table_name})
        return normalized

    def search_tables(self, request: CsmarTableSearchRequest) -> list[CsmarTableCandidate]:
        payload = self._call_mcp_tool(
            "csmar_search_tables",
            {
                "query": request.query,
                "database_name": request.database_name,
                "limit": max(1, min(request.limit, 5)),
            },
        ).content
        items = payload.get("items")
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
            raise CsmarMetadataError("MCP 返回的搜索结果格式非法。", code="upstream_error")

        normalized: list[CsmarTableCandidate] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            table_code = str(item.get("table_code") or "").strip()
            if not table_code:
                continue
            normalized.append(
                CsmarTableCandidate(
                    table_code=table_code,
                    table_name=str(item.get("table_name") or table_code).strip(),
                    database_name=str(item.get("database_name") or "").strip(),
                    score=float(item.get("score") or 0.0),
                    why_matched=str(item.get("why_matched") or "").strip(),
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

    def search_fields(self, request: CsmarFieldSearchRequest) -> list[CsmarFieldSearchHit]:
        payload = self._call_mcp_tool(
            "csmar_search_fields",
            {
                "query": request.query,
                "database_name": request.database_name,
                "table_code": request.table_code,
                "role_hint": request.role_hint,
                "frequency_hint": request.frequency_hint,
                "limit": max(1, min(request.limit, 20)),
            },
        ).content
        items = payload.get("items")
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
            raise CsmarMetadataError(
                "MCP 返回的字段检索结果格式非法。", code="upstream_error"
            )

        normalized: list[CsmarFieldSearchHit] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            table_code = str(item.get("table_code") or "").strip()
            field_name = str(item.get("field_name") or "").strip()
            if not table_code or not field_name:
                continue
            normalized.append(
                CsmarFieldSearchHit(
                    field_name=field_name,
                    field_label=str(item.get("field_label") or "").strip(),
                    field_description=str(item.get("field_description") or "").strip(),
                    data_type=str(item.get("data_type") or "").strip(),
                    frequency_tags=normalize_tags(item.get("frequency_tags")),
                    role_tags=normalize_tags(item.get("role_tags")),
                    table_code=table_code,
                    table_name=str(item.get("table_name") or table_code).strip(),
                    database_name=str(item.get("database_name") or "").strip(),
                    why_matched=str(item.get("why_matched") or "").strip(),
                    score=float(item.get("score") or 0.0),
                )
            )
        return normalized

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
        if "files" not in payload:
            raise CsmarMetadataError(
                "MCP materialize 返回缺少文件列表。", code="upstream_error"
            )
        return CsmarMaterializeQueryResult(
            validation_id=validation_id,
            output_dir=output_dir,
            files=[str(item) for item in normalize_tags(payload.get("files"))],
        )

    def fetch(self, plan: QueryPlan, output_dir: Path) -> Path:
        return output_dir / f"{plan.table_name}.parquet"

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        try:
            probe_payload = self.probe_query(
                table_code=request.table_name,
                columns=[request.field_name],
                condition=build_query_condition(request.field_name),
                start_date=f"{request.time_start_year}-01-01",
                end_date=f"{request.time_end_year}-12-31",
                sample_rows=0,
            )
        except CsmarMetadataError as exc:
            return CsmarFieldProbeResult(
                variable_name=request.variable_name,
                table_name=request.table_name,
                field_name=request.field_name,
                field_exists=False,
                query_fingerprint=f"{request.table_name}.{request.field_name}",
                scope_level="time_scoped",
                vendor_message=exc.vendor_message,
                retriable=exc.retriable,
                warnings=probe_scope_warnings(request.entity_scope),
            )

        field_exists = request.field_name not in probe_payload.invalid_columns
        row_count = probe_payload.row_count
        query_fingerprint = probe_payload.query_fingerprint.strip()
        if not query_fingerprint:
            query_fingerprint = f"{request.table_name}.{request.field_name}"

        return CsmarFieldProbeResult(
            variable_name=request.variable_name,
            table_name=request.table_name,
            field_name=request.field_name,
            field_exists=field_exists,
            row_count=row_count,
            query_fingerprint=query_fingerprint,
            scope_level="time_scoped",
            warnings=probe_scope_warnings(request.entity_scope),
        )

    def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpToolPayload:
        caller = self._get_mcp_tool_caller()
        sanitized_args = {k: v for k, v in arguments.items() if v is not None}
        return caller.call_tool(tool_name, sanitized_args)

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

# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from stata_agent.providers.csmar import CsmarMetadataError
from stata_agent.providers.csmar import NodeScopedCsmarProvider
from stata_agent.providers.csmar.types import CsmarGetTableSchemaToolResult
from stata_agent.providers.csmar.types import CsmarListDatabasesToolResult
from stata_agent.providers.csmar.types import CsmarListTablesToolResult
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort


class VariableMappingToolkit:
    def __init__(self, metadata_provider: CsmarMetadataProviderPort) -> None:
        self._metadata_provider = metadata_provider

    def build_tools(self) -> list[BaseTool]:
        provider = self._metadata_provider

        @tool("csmar_list_databases")
        def list_databases() -> CsmarListDatabasesToolResult:
            """列出已购买数据库。映射节点必须先通过该工具确定数据库范围。"""
            try:
                databases = provider.list_databases()
            except CsmarMetadataError as exc:
                return _database_error_payload(exc, _last_trace_id(provider))
            return CsmarListDatabasesToolResult(
                ok=True,
                databases=databases,
                trace_id=_last_trace_id(provider),
            )

        @tool("csmar_list_tables")
        def list_tables(database_name: str) -> CsmarListTablesToolResult:
            """列出指定数据库下的数据表。database_name 必须逐字复制自 csmar_list_databases。"""
            try:
                items = provider.list_tables(database_name)
            except CsmarMetadataError as exc:
                return _table_error_payload(exc, _last_trace_id(provider), database_name)
            return CsmarListTablesToolResult(
                ok=True,
                database_name=database_name,
                items=items,
                trace_id=_last_trace_id(provider),
            )

        @tool("csmar_get_table_schema")
        def get_table_schema(table_code: str) -> CsmarGetTableSchemaToolResult:
            """读取单张表的字段 schema。只有该工具能证明字段存在。"""
            try:
                schema = provider.get_table_schema(table_code)
            except CsmarMetadataError as exc:
                return _schema_error_payload(exc, _last_trace_id(provider), table_code)
            return CsmarGetTableSchemaToolResult(
                ok=True,
                table_code=schema.table_code,
                table_name=schema.table_name,
                database_name=schema.database_name,
                fields=schema.fields,
                trace_id=_last_trace_id(provider),
            )

        return [list_databases, list_tables, get_table_schema]


def _database_error_payload(
    error: CsmarMetadataError,
    trace_id: str,
) -> CsmarListDatabasesToolResult:
    return CsmarListDatabasesToolResult(
        ok=False,
        code=error.code,
        message=str(error),
        hint=error.hint,
        trace_id=trace_id,
    )


def _table_error_payload(
    error: CsmarMetadataError,
    trace_id: str,
    database_name: str,
) -> CsmarListTablesToolResult:
    return CsmarListTablesToolResult(
        ok=False,
        database_name=database_name,
        code=error.code,
        message=str(error),
        hint=error.hint,
        trace_id=trace_id,
    )


def _schema_error_payload(
    error: CsmarMetadataError,
    trace_id: str,
    table_code: str,
) -> CsmarGetTableSchemaToolResult:
    return CsmarGetTableSchemaToolResult(
        ok=False,
        table_code=table_code,
        code=error.code,
        message=str(error),
        hint=error.hint,
        trace_id=trace_id,
    )


def _last_trace_id(provider: CsmarMetadataProviderPort) -> str:
    if isinstance(provider, NodeScopedCsmarProvider):
        return provider.last_trace_id
    return ""

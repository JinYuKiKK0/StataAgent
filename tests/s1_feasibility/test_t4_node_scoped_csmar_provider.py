"""S1-T4 节点级 CSMAR 工具预算与白名单测试。"""

from stata_agent.providers.csmar import CsmarMetadataError
from stata_agent.providers.csmar.node_scoped_client import NodeScopedCsmarProvider
from stata_agent.services.mapping.contracts import CsmarFieldProbeRequest
from stata_agent.services.mapping.contracts import CsmarFieldProbeResult
from stata_agent.services.mapping.contracts import CsmarSchemaField
from stata_agent.services.mapping.contracts import CsmarTableRecord
from stata_agent.services.mapping.contracts import CsmarTableSchema
from stata_agent.services.mapping.contracts import VariableMappingBudget


class _FakeMetadataProvider:
    def __init__(self) -> None:
        self.list_databases_calls = 0
        self.list_tables_calls: list[str] = []
        self.schema_calls: list[str] = []
        self.probe_calls: list[tuple[str, str]] = []

    def list_databases(self) -> list[str]:
        self.list_databases_calls += 1
        return ["财务报表"]

    def list_tables(self, database_name: str) -> list[CsmarTableRecord]:
        self.list_tables_calls.append(database_name)
        return [
            CsmarTableRecord(
                table_code="FS_Comins",
                table_name="利润表",
                database_name=database_name,
            )
        ]

    def get_table_schema(self, table_code: str) -> CsmarTableSchema:
        self.schema_calls.append(table_code)
        return CsmarTableSchema(
            table_code=table_code,
            table_name="利润表",
            database_name="财务报表",
            fields=[
                CsmarSchemaField(
                    field_name="ROA",
                    field_label="资产回报率",
                    frequency_tags=["annual"],
                )
            ],
        )

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        self.probe_calls.append((request.table_code, request.field_name))
        return CsmarFieldProbeResult(
            variable_name=request.variable_name,
            table_code=request.table_code,
            field_name=request.field_name,
            field_exists=True,
            row_count=1,
        )


def test_node_scoped_provider_rejects_disallowed_tools() -> None:
    """验证节点只暴露白名单工具，探针节点能力不会泄漏到映射节点。"""
    provider = NodeScopedCsmarProvider(
        metadata_provider=_FakeMetadataProvider(),
        node_name="map_variables",
        allowed_tools={
            "csmar_list_databases",
            "csmar_list_tables",
            "csmar_get_table_schema",
        },
        budget=VariableMappingBudget(),
    )

    try:
        provider.probe_field_availability(
            CsmarFieldProbeRequest(
                variable_name="ROA",
                table_code="FS_Comins",
                field_name="ROA",
                entity_scope="A股上市公司",
                time_start_year=2010,
                time_end_year=2023,
            )
        )
    except CsmarMetadataError as error:
        assert error.code == "tool_not_allowed"
    else:
        raise AssertionError("expected tool_not_allowed error")


def test_node_scoped_provider_returns_budget_exhausted_after_limit() -> None:
    """验证节点预算耗尽后会立即返回 budget_exhausted，而不是继续消耗额度。"""
    provider = NodeScopedCsmarProvider(
        metadata_provider=_FakeMetadataProvider(),
        node_name="map_variables",
        allowed_tools={"csmar_list_tables"},
        budget=VariableMappingBudget(
            list_databases_limit=0,
            list_tables_limit=1,
            schema_reads_limit=0,
            max_total_calls=1,
        ),
    )

    first_result = provider.list_tables("财务报表")
    assert first_result[0].table_code == "FS_Comins"

    try:
        provider.list_tables("财务报表")
    except CsmarMetadataError as error:
        assert error.code == "budget_exhausted"
    else:
        raise AssertionError("expected budget_exhausted error")

    traces = provider.drain_tool_traces()
    assert traces[-1].tool_name == "csmar_list_tables"
    assert traces[-1].error is not None
    assert traces[-1].error.get("code") == "budget_exhausted"

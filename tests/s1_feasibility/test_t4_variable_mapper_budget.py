"""S1-T4 变量映射预算与辅助路径测试。"""

from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import VariableMappingBudget
from stata_agent.services.variable_mapper import VariableMapper
from tests.s1_feasibility.t4_variable_mapper_support import build_definitions
from tests.s1_feasibility.t4_variable_mapper_support import build_request
from tests.s1_feasibility.t4_variable_mapper_support import build_spec
from tests.s1_feasibility.t4_variable_mapper_support import FakeMetadataProvider
from tests.s1_feasibility.t4_variable_mapper_support import make_schema_field
from tests.s1_feasibility.t4_variable_mapper_support import make_search_hit
from tests.s1_feasibility.t4_variable_mapper_support import make_table_candidate


def test_mapper_respects_per_variable_budget_limits() -> None:
    """验证每变量 search_tables/get_table_schema 预算上限会被严格执行。"""
    provider = FakeMetadataProvider(
        tables={
            "ROA": [
                make_table_candidate("T1", table_name="表1", database_name="财务", score=0.9),
                make_table_candidate("T2", table_name="表2", database_name="财务", score=0.8),
                make_table_candidate("T3", table_name="表3", database_name="财务", score=0.7),
            ]
        },
        schemas={
            "T1": CsmarTableSchema(
                table_code="T1",
                fields=[make_schema_field("ROA", field_label="ROA", frequency_tags=[])],
            ),
            "T2": CsmarTableSchema(
                table_code="T2",
                fields=[
                    make_schema_field(
                        "ROAA",
                        field_label="总资产收益率",
                        frequency_tags=[],
                    )
                ],
            ),
            "T3": CsmarTableSchema(
                table_code="T3",
                fields=[make_schema_field("R3", field_label="其他", frequency_tags=[])],
            ),
        },
    )
    mapper = VariableMapper(
        metadata_provider=provider,
        mapping_budget=VariableMappingBudget(
            search_tables_limit=1,
            schema_reads_limit=2,
            search_fields_limit=0,
            enable_aux_field_search=False,
        ),
    )

    result = mapper.map_probe_bindings(
        request=build_request(),
        spec=build_spec(),
        variable_definitions=[build_definitions()[0]],
    )

    assert result.failure_reason is None
    assert len(provider.search_tables_calls) == 1
    assert len(provider.get_table_schema_calls) == 2


def test_mapper_uses_search_fields_as_verified_auxiliary_path() -> None:
    """验证 search_fields 只作为辅助路径，命中后仍需经过 schema 复核。"""
    provider = FakeMetadataProvider(
        tables={
            "资产总计": [
                make_table_candidate(
                    "FS_Comins",
                    table_name="利润表",
                    database_name="财务报表",
                    score=0.9,
                )
            ]
        },
        schemas={
            "FS_Comins": CsmarTableSchema(
                table_code="FS_Comins",
                table_name="利润表",
                database_name="财务报表",
                fields=[
                    make_schema_field(
                        "NOT_ASSET",
                        field_label="非目标字段",
                        frequency_tags=["annual"],
                    )
                ],
            ),
            "FS_Combas": CsmarTableSchema(
                table_code="FS_Combas",
                table_name="资产负债表",
                database_name="财务报表",
                fields=[
                    make_schema_field(
                        "ASSET",
                        field_label="总资产",
                        frequency_tags=["annual", "quarterly"],
                    )
                ],
            ),
        },
        search_hits={
            "资产总计": [
                make_search_hit(
                    table_code="FS_Combas",
                    table_name="资产负债表",
                    database_name="财务报表",
                    field_name="ASSET",
                    field_label="总资产",
                )
            ]
        },
    )
    mapper = VariableMapper(metadata_provider=provider)

    result = mapper.map_probe_bindings(
        request=build_request(),
        spec=build_spec(),
        variable_definitions=[build_definitions()[1]],
    )

    assert result.failure_reason is None
    assert len(provider.search_fields_calls) == 1
    assert "FS_Combas" in provider.get_table_schema_calls
    binding = result.bindings[0]
    assert binding.table_name == "FS_Combas"
    assert binding.field_name == "ASSET"

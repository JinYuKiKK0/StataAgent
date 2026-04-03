"""S1-T4 变量映射核心行为测试。"""

from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import VariableDefinition
from stata_agent.domains.mapping.types import VariableMatchDecision
from stata_agent.services.variable_mapper import VariableMapper
from tests.s1_feasibility.t4_variable_mapper_support import build_definitions
from tests.s1_feasibility.t4_variable_mapper_support import build_request
from tests.s1_feasibility.t4_variable_mapper_support import build_spec
from tests.s1_feasibility.t4_variable_mapper_support import FakeMetadataProvider
from tests.s1_feasibility.t4_variable_mapper_support import FakeSemanticJudge
from tests.s1_feasibility.t4_variable_mapper_support import make_schema_field
from tests.s1_feasibility.t4_variable_mapper_support import make_search_hit
from tests.s1_feasibility.t4_variable_mapper_support import make_table_candidate


def test_mapper_uses_semantic_judge_for_synonymous_field_names() -> None:
    """验证字面不同但语义等价的变量名会通过语义判别映射到同一字段。"""
    provider = FakeMetadataProvider(
        tables={
            "ROA": [
                make_table_candidate(
                    "FS_Comins",
                    table_name="利润表",
                    database_name="财务报表",
                    score=0.9,
                )
            ],
            "资产总计": [
                make_table_candidate(
                    "FS_Combas",
                    table_name="资产负债表",
                    database_name="财务报表",
                    score=0.92,
                )
            ],
        },
        schemas={
            "FS_Comins": CsmarTableSchema(
                table_code="FS_Comins",
                table_name="利润表",
                database_name="财务报表",
                fields=[
                    make_schema_field(
                        "ROA",
                        field_label="资产回报率",
                        frequency_tags=["annual", "quarterly"],
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
    judge = FakeSemanticJudge(
        {
            "ROA": VariableMatchDecision(
                matched=True,
                selected_table_name="FS_Comins",
                selected_field_name="ROA",
                confidence=0.95,
                rationale="ROA 与候选字段完全一致。",
                resolved_domain="财务报表",
            ),
            "资产总计": VariableMatchDecision(
                matched=True,
                selected_table_name="FS_Combas",
                selected_field_name="ASSET",
                confidence=0.92,
                rationale="资产总计与总资产语义等价。",
                resolved_domain="财务报表",
            ),
        }
    )
    mapper = VariableMapper(metadata_provider=provider, semantic_judge=judge)

    result = mapper.map_probe_bindings(
        request=build_request(),
        spec=build_spec(),
        variable_definitions=build_definitions(),
    )

    assert result.failure_reason is None
    binding = next(item for item in result.bindings if item.variable_name == "资产总计")
    assert binding.field_name == "ASSET"
    assert binding.source == "csmar_semantic_judge"
    resolved = next(
        item
        for item in result.resolved_variable_definitions
        if item.variable_name == "资产总计"
    )
    assert resolved.source_domain_hint == "财务报表"


def test_mapper_fails_fast_when_hard_variable_has_no_schema_candidate() -> None:
    """验证 Hard Contract 变量在 schema 内无可用候选时会触发失败。"""
    provider = FakeMetadataProvider(
        tables={
            "ROA": [
                make_table_candidate(
                    "FS_Comins",
                    table_name="利润表",
                    database_name="财务报表",
                    score=0.9,
                )
            ],
            "资产总计": [
                make_table_candidate(
                    "FS_Combas",
                    table_name="资产负债表",
                    database_name="财务报表",
                    score=0.92,
                )
            ],
        },
        schemas={
            "FS_Comins": CsmarTableSchema(
                table_code="FS_Comins",
                fields=[
                    make_schema_field(
                        "ROA",
                        field_label="资产回报率",
                        frequency_tags=["annual"],
                    )
                ],
            ),
            "FS_Combas": CsmarTableSchema(
                table_code="FS_Combas",
                fields=[
                    make_schema_field(
                        "LIABILITY",
                        field_label="总负债",
                        frequency_tags=["annual"],
                    )
                ],
            ),
        },
    )
    mapper = VariableMapper(metadata_provider=provider)

    result = mapper.map_probe_bindings(
        request=build_request(),
        spec=build_spec(),
        variable_definitions=build_definitions(),
    )

    assert result.failure_reason is not None
    assert "资产总计" in result.failure_reason
    assert result.bindings == []


def test_mapper_keeps_soft_gap_summary_without_abort() -> None:
    """验证 Soft Contract 缺口只进入摘要，不会导致整个映射阶段失败。"""
    provider = FakeMetadataProvider(
        tables={
            "ROA": [
                make_table_candidate(
                    "FS_Comins",
                    table_name="利润表",
                    database_name="财务报表",
                    score=0.9,
                )
            ],
            "资产总计": [
                make_table_candidate(
                    "FS_Combas",
                    table_name="资产负债表",
                    database_name="财务报表",
                    score=0.92,
                )
            ],
        },
        schemas={
            "FS_Comins": CsmarTableSchema(
                table_code="FS_Comins",
                fields=[
                    make_schema_field(
                        "ROA",
                        field_label="资产回报率",
                        frequency_tags=["annual"],
                    )
                ],
            ),
            "FS_Combas": CsmarTableSchema(
                table_code="FS_Combas",
                fields=[
                    make_schema_field(
                        "ASSET",
                        field_label="总资产",
                        frequency_tags=["annual"],
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
    definitions = build_definitions() + [
        VariableDefinition(
            variable_name="不存在的控制变量",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
            source_domain_hint="pending_resolution",
        )
    ]

    result = mapper.map_probe_bindings(
        request=build_request(),
        spec=build_spec(),
        variable_definitions=definitions,
    )

    assert result.failure_reason is None
    assert "不存在的控制变量" in result.soft_contract_gaps

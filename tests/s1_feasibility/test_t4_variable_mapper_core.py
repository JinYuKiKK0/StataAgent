"""S1-T4 变量映射核心行为测试。"""

from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarTableRecord
from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import VariableMappingPlanItem
from stata_agent.domains.mapping.types import VariableMappingPlanResult
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.mapping.ports import CsmarMetadataProviderPort
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.variable_mapper import VariableMapper
from stata_agent.services.variable_requirements_builder import VariableRequirementsBuilder


class _UnusedMetadataProvider:
    def list_databases(self) -> list[str]:
        raise AssertionError("该测试通过 fake planner 驱动，不应访问真实 metadata provider。")

    def list_tables(self, database_name: str) -> list[CsmarTableRecord]:
        raise AssertionError("该测试通过 fake planner 驱动，不应访问真实 metadata provider。")

    def get_table_schema(self, table_code: str) -> CsmarTableSchema:
        raise AssertionError("该测试通过 fake planner 驱动，不应访问真实 metadata provider。")

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        raise AssertionError("变量映射测试不应调用 probe。")


class _FakePlanningAgent:
    def __init__(self, result: VariableMappingPlanResult) -> None:
        self._result = result

    def plan(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        metadata_provider: CsmarMetadataProviderPort,
    ) -> VariableMappingPlanResult:
        return self._result


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="企业资产规模与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资产总计"],
        entity_scope="A股上市公司",
        time_range="2018-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="企业资产规模与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资产总计"],
        entity_scope="A股上市公司",
        time_start_year=2018,
        time_end_year=2023,
        control_variable_candidates=["资产负债率"],
        analysis_grain_candidates=["firm-year"],
        analysis_frequency_hint="annual",
    )


def _build_definitions() -> list[VariableDefinition]:
    builder = VariableRequirementsBuilder()
    return builder.build(_build_spec()).variable_definitions


def _materialize_from_planner(
    mapper: VariableMapper,
    *,
    variable_definitions: list[VariableDefinition] | None = None,
) -> VariableMappingResult:
    definitions = variable_definitions or _build_definitions()
    plan_result = mapper.plan_probe_mapping(
        request=_build_request(),
        spec=_build_spec(),
        variable_definitions=definitions,
    )
    return mapper.materialize_variable_bindings(
        request=_build_request(),
        spec=_build_spec(),
        variable_definitions=definitions,
        planning_result=plan_result,
    )


def test_mapper_builds_bindings_from_planner_selection() -> None:
    """验证 mapper 会把 planner 产出的结构化映射草案转换为正式绑定。"""
    planner = _FakePlanningAgent(
        VariableMappingPlanResult(
            items=[
                VariableMappingPlanItem(
                    variable_name="ROA",
                    matched=True,
                    database_name="财务报表",
                    table_code="FS_Comins",
                    table_name="利润表",
                    field_name="ROA",
                    field_label="资产回报率",
                    frequency_match=True,
                    evidence="已通过利润表 schema 确认。",
                    trace_id="trace_roa_schema",
                ),
                VariableMappingPlanItem(
                    variable_name="资产总计",
                    matched=True,
                    database_name="财务报表",
                    table_code="FS_Combas",
                    table_name="资产负债表",
                    field_name="ASSET",
                    field_label="总资产",
                    frequency_match=True,
                    evidence="已通过资产负债表 schema 确认。",
                    trace_id="trace_asset_schema",
                ),
                VariableMappingPlanItem(
                    variable_name="资产负债率",
                    matched=False,
                    rationale="当前预算内未找到语义等价字段。",
                ),
            ]
        )
    )
    mapper = VariableMapper(
        metadata_provider=_UnusedMetadataProvider(),
        planner=planner,
    )

    result = _materialize_from_planner(mapper)

    assert result.failure_reason is None
    assert [item.variable_name for item in result.bindings] == ["ROA", "资产总计"]
    binding = next(item for item in result.bindings if item.variable_name == "资产总计")
    assert binding.table_code == "FS_Combas"
    assert binding.field_name == "ASSET"
    assert binding.trace_id == "trace_asset_schema"
    assert binding.source == "csmar_llm_mapping_agent"


def test_mapper_fails_fast_when_planner_misses_hard_variable() -> None:
    """验证 planner 未能解析 Hard Contract 变量时 mapper 会触发失败。"""
    planner = _FakePlanningAgent(
        VariableMappingPlanResult(
            items=[
                VariableMappingPlanItem(
                    variable_name="ROA",
                    matched=True,
                    database_name="财务报表",
                    table_code="FS_Comins",
                    field_name="ROA",
                    frequency_match=True,
                    trace_id="trace_roa_schema",
                ),
                VariableMappingPlanItem(
                    variable_name="资产总计",
                    matched=False,
                    rationale="未找到可确认的字段。",
                ),
            ]
        )
    )
    mapper = VariableMapper(
        metadata_provider=_UnusedMetadataProvider(),
        planner=planner,
    )

    result = _materialize_from_planner(mapper)

    assert result.failure_reason is not None
    assert "资产总计" in result.failure_reason
    assert result.bindings == []


def test_mapper_keeps_soft_gap_summary_without_abort() -> None:
    """验证 planner 未解决 Soft Contract 变量时 mapper 仅记录缺口摘要。"""
    planner = _FakePlanningAgent(
        VariableMappingPlanResult(
            items=[
                VariableMappingPlanItem(
                    variable_name="ROA",
                    matched=True,
                    database_name="财务报表",
                    table_code="FS_Comins",
                    field_name="ROA",
                    frequency_match=True,
                    trace_id="trace_roa_schema",
                ),
                VariableMappingPlanItem(
                    variable_name="资产总计",
                    matched=True,
                    database_name="财务报表",
                    table_code="FS_Combas",
                    field_name="ASSET",
                    frequency_match=True,
                    trace_id="trace_asset_schema",
                ),
                VariableMappingPlanItem(
                    variable_name="不存在的控制变量",
                    matched=False,
                    rationale="预算耗尽前未找到可接受字段。",
                ),
            ]
        )
    )
    mapper = VariableMapper(
        metadata_provider=_UnusedMetadataProvider(),
        planner=planner,
    )
    definitions = _build_definitions() + [
        VariableDefinition(
            variable_name="不存在的控制变量",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
            source_domain_hint="pending_resolution",
        )
    ]

    result = _materialize_from_planner(
        mapper,
        variable_definitions=definitions,
    )

    assert result.failure_reason is None
    assert "不存在的控制变量" in result.soft_contract_gaps

"""S1-T4 变量映射核心行为测试。"""

from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.services.mapping.contracts import CsmarFieldProbeRequest
from stata_agent.services.mapping.contracts import CsmarFieldProbeResult
from stata_agent.services.mapping.contracts import CsmarTableRecord
from stata_agent.services.mapping.contracts import CsmarTableSchema
from stata_agent.services.mapping.contracts import MappingPlannerInput
from stata_agent.services.mapping.contracts import VariableMappingBudget
from stata_agent.services.mapping.contracts import VariableMappingPlanItem
from stata_agent.services.mapping.contracts import VariableMappingPlanResult
from stata_agent.services.mapping.contracts import VariableMappingResult
from stata_agent.services.mapping.materialize_bindings import (
    VariableBindingMaterializer,
)
from stata_agent.services.mapping.plan_mapping import ProbeMappingPlanner
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.spec.variable_requirements import VariableRequirementsBuilder


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

    def drain_tool_traces(self) -> list[object]:
        return []


class _PassThroughScopeFactory:
    def create_mapping_provider(
        self,
        metadata_provider: CsmarMetadataProviderPort,
        budget: VariableMappingBudget,
    ) -> _UnusedMetadataProvider:
        del budget
        assert isinstance(metadata_provider, _UnusedMetadataProvider)
        return metadata_provider


class _FakePlanningAgent:
    def __init__(self, result: VariableMappingPlanResult) -> None:
        self._result = result

    def plan(
        self,
        *,
        planner_input: MappingPlannerInput,
        metadata_provider: CsmarMetadataProviderPort,
    ) -> VariableMappingPlanResult:
        del planner_input, metadata_provider
        return self._result


def _build_definitions() -> list[VariableDefinition]:
    builder = VariableRequirementsBuilder()
    return builder.build(_build_spec()).variable_definitions


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
        empirical_requirements="构建基准双向固定效应模型",
    )


def _build_planner_input(
    variable_definitions: list[VariableDefinition] | None = None,
) -> MappingPlannerInput:
    return MappingPlannerInput(
        topic="企业资产规模与盈利能力",
        entity_scope="A股上市公司",
        time_start_year=2018,
        time_end_year=2023,
        analysis_frequency_hint="annual",
        analysis_grain_candidates=["firm-year"],
        variable_definitions=variable_definitions or [],
    )


def _build_mapping_components(
    result: VariableMappingPlanResult,
) -> tuple[ProbeMappingPlanner, VariableBindingMaterializer]:
    planner = ProbeMappingPlanner(
        metadata_provider=_UnusedMetadataProvider(),
        planner=_FakePlanningAgent(result),
        scope_factory=_PassThroughScopeFactory(),
    )
    return planner, VariableBindingMaterializer()


def _materialize_from_planner(
    planner: ProbeMappingPlanner,
    materializer: VariableBindingMaterializer,
    *,
    variable_definitions: list[VariableDefinition] | None = None,
) -> VariableMappingResult:
    definitions = variable_definitions or _build_definitions()
    plan_result = planner.plan_probe_mapping(
        planner_input=_build_planner_input(definitions),
    )
    return materializer.materialize_variable_bindings(
        variable_definitions=definitions,
        planning_result=plan_result,
    )


def test_mapper_builds_bindings_from_planner_selection() -> None:
    """验证 mapper 会把 planner 产出的结构化映射草案转换为正式绑定。"""
    planner, materializer = _build_mapping_components(
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

    result = _materialize_from_planner(planner, materializer)

    assert result.failure_reason is None
    assert [item.variable_name for item in result.bindings] == ["ROA", "资产总计"]
    binding = next(item for item in result.bindings if item.variable_name == "资产总计")
    assert binding.table_code == "FS_Combas"
    assert binding.field_name == "ASSET"
    assert binding.contract_tier == "hard"
    assert set(binding.model_dump(mode="json")) == {
        "variable_name",
        "table_code",
        "field_name",
        "contract_tier",
        "frequency_match",
        "substituted_from",
    }


def test_mapper_fails_fast_when_planner_misses_hard_variable() -> None:
    """验证 planner 未能解析 Hard Contract 变量时 mapper 会触发失败。"""
    planner, materializer = _build_mapping_components(
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

    result = _materialize_from_planner(planner, materializer)

    assert result.failure_reason is not None
    assert "资产总计" in result.failure_reason
    assert result.bindings == []

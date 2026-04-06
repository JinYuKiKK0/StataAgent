"""Phase 1 终态清理测试。"""

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.providers.audit import InMemoryAuditStore
from stata_agent.services.contract.data_contract_builder import DataContractBuilder
from stata_agent.services.mapping.contracts import VariableMappingPlanItem
from stata_agent.services.mapping.contracts import VariableMappingPlanResult
from stata_agent.services.mapping.materialize_bindings import VariableBindingMaterializer
from stata_agent.services.probe.contracts import VariableProbeResult
from stata_agent.services.probe.summarizer import ProbeCoverageSummarizer
from stata_agent.services.spec.contracts import RequirementParseResult
from stata_agent.services.spec.variable_requirements import VariableRequirementsBuilder
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator
from stata_agent.workflow.types import RunStage


class _SuccessParser:
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(
            spec=ResearchSpec(
                topic=request.topic,
                dependent_variable=request.dependent_variable,
                independent_variables=request.independent_variables,
                entity_scope=request.entity_scope or "A股上市银行",
                time_start_year=2018,
                time_end_year=2023,
                analysis_frequency_hint="annual",
                analysis_grain_candidates=["bank-year"],
                control_variable_candidates=["资本充足率"],
            )
        )


class _StaticPlanner:
    def plan_probe_mapping(self, *args: object, **kwargs: object) -> VariableMappingPlanResult:
        del args, kwargs
        return VariableMappingPlanResult(
            items=[
                VariableMappingPlanItem(
                    variable_name="ROA",
                    matched=True,
                    table_code="BANK_INDEX",
                    field_name="ROAA",
                    frequency_match=True,
                ),
                VariableMappingPlanItem(
                    variable_name="资本充足率",
                    matched=True,
                    table_code="BANK_CAPITAL",
                    field_name="CAPITAL_ADEQUACY",
                    frequency_match=True,
                ),
            ]
        )

    def drain_tool_traces(self) -> list[object]:
        return []


class _StaticProbeExecutor:
    def run_field_probes(self, *args: object, **kwargs: object) -> list[VariableProbeResult]:
        del args, kwargs
        return [
            VariableProbeResult(
                variable_name="ROA",
                contract_tier="hard",
                table_code="BANK_INDEX",
                field_name="ROAA",
                field_exists=True,
                frequency_match=True,
                query_count=120,
                is_accessible=True,
            ),
            VariableProbeResult(
                variable_name="资本充足率",
                contract_tier="soft",
                table_code="BANK_CAPITAL",
                field_name="CAPITAL_ADEQUACY",
                field_exists=True,
                frequency_match=True,
                query_count=120,
                is_accessible=True,
            ),
        ]

    def drain_tool_traces(self) -> list[object]:
        return []


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行资本充足率与ROA",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_range="2018-2023",
        empirical_requirements="构建基准回归模型",
    )


def test_phase1_keeps_only_contract_in_active_state_after_contract_build() -> None:
    """验证 S1 完成后 active state 不再常驻中间 mapping/probe 工件。"""
    orchestrator = Phase1FeasibilityOrchestrator(
        parser=_SuccessParser(),
        builder=VariableRequirementsBuilder(),
        mapping_planner=_StaticPlanner(),
        binding_materializer=VariableBindingMaterializer(),
        probe_executor=_StaticProbeExecutor(),
        probe_summarizer=ProbeCoverageSummarizer(),
        data_contract_builder=DataContractBuilder(),
        audit_store=InMemoryAuditStore(),
    )

    state = orchestrator.run_feasibility(ResearchState(request=_build_request()))

    assert state.stage is RunStage.CONTRACTED
    assert state.phase1_artifacts.data_contract_bundle is not None
    assert state.phase1_artifacts.spec is None
    assert state.phase1_artifacts.variable_definitions is None
    assert state.phase1_artifacts.data_requirements_draft is None
    assert state.phase1_artifacts.variable_bindings is None
    assert state.phase1_artifacts.probe_coverage_result is None

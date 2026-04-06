from __future__ import annotations

from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.fetch.types import VariableProbeResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingPlanResult
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.domains.spec.types import VariableRequirementsResult
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator
from tests.s1_feasibility.phase1_subgraph_artifacts import build_contract
from tests.s1_feasibility.phase1_subgraph_artifacts import build_coverage_result
from tests.s1_feasibility.phase1_subgraph_artifacts import build_mapping_result
from tests.s1_feasibility.phase1_subgraph_artifacts import build_parse_result
from tests.s1_feasibility.phase1_subgraph_artifacts import build_plan_result
from tests.s1_feasibility.phase1_subgraph_artifacts import build_probe_results
from tests.s1_feasibility.phase1_subgraph_artifacts import build_builder_result


class FakeParser:
    def __init__(self, result: RequirementParseResult) -> None:
        self._result = result

    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        return self._result


class FakeBuilder:
    def __init__(self, result: VariableRequirementsResult) -> None:
        self._result = result

    def build(self, spec: ResearchSpec) -> VariableRequirementsResult:
        return self._result


class FakeMapper:
    def __init__(
        self,
        plan_result: VariableMappingPlanResult,
        materialized_result: VariableMappingResult,
    ) -> None:
        self._plan_result = plan_result
        self._materialized_result = materialized_result

    def plan_probe_mapping(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingPlanResult:
        return self._plan_result

    def materialize_variable_bindings(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        planning_result: VariableMappingPlanResult,
    ) -> VariableMappingResult:
        return self._materialized_result

    def drain_tool_traces(self) -> list[object]:
        return []

    def map_probe_bindings(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingResult:
        plan = self.plan_probe_mapping(
            request=request,
            spec=spec,
            variable_definitions=variable_definitions,
        )
        return self.materialize_variable_bindings(
            request=request,
            spec=spec,
            variable_definitions=variable_definitions,
            planning_result=plan,
        )


class FakeProbeExecutor:
    def __init__(
        self,
        raw_results: list[VariableProbeResult],
        coverage_result: ProbeCoverageResult,
    ) -> None:
        self._raw_results = raw_results
        self._coverage_result = coverage_result

    def run_field_probes(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> list[VariableProbeResult]:
        return self._raw_results

    def summarize_coverage(
        self,
        spec: ResearchSpec,
        probe_results: list[VariableProbeResult],
    ) -> ProbeCoverageResult:
        return self._coverage_result

    def drain_tool_traces(self) -> list[object]:
        return []

    def execute_coverage(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> ProbeCoverageResult:
        raw_results = self.run_field_probes(spec, variable_bindings)
        return self.summarize_coverage(spec, raw_results)


class FakeContractBuilder:
    def __init__(self, contract: DataContractBundle) -> None:
        self._contract = contract

    def build(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        variable_bindings: list[VariableBinding],
        probe_coverage: ProbeCoverageResult,
    ) -> DataContractBundle:
        return self._contract
def build_orchestrator(
    *,
    parse_result: RequirementParseResult | None = None,
    mapping_result: VariableMappingResult | None = None,
    coverage_result: ProbeCoverageResult | None = None,
) -> Phase1FeasibilityOrchestrator:
    return Phase1FeasibilityOrchestrator(
        parser=FakeParser(parse_result or build_parse_result()),
        builder=FakeBuilder(build_builder_result()),
        mapper=FakeMapper(build_plan_result(), mapping_result or build_mapping_result()),
        probe_executor=FakeProbeExecutor(
            build_probe_results(),
            coverage_result or build_coverage_result(),
        ),
        data_contract_builder=FakeContractBuilder(build_contract()),
    )

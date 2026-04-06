from typing import Protocol

from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.fetch.types import VariableProbeResult
from stata_agent.domains.mapping.ports import CsmarMetadataProviderPort
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingPlanResult
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.domains.spec.types import VariableRequirementsResult
from langchain_core.runnables.config import RunnableConfig
from stata_agent.workflow.state import ResearchState


class RequirementParserPort(Protocol):
    def parse(self, request: ResearchRequest) -> RequirementParseResult: ...


class VariableRequirementsBuilderPort(Protocol):
    def build(self, spec: ResearchSpec) -> VariableRequirementsResult: ...


class VariableMapperPort(Protocol):
    def plan_probe_mapping(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingPlanResult: ...

    def materialize_variable_bindings(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        planning_result: VariableMappingPlanResult,
    ) -> VariableMappingResult: ...


class ProbeExecutorPort(Protocol):
    def run_field_probes(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> list[VariableProbeResult]: ...

    def summarize_coverage(
        self,
        spec: ResearchSpec,
        probe_results: list[VariableProbeResult],
    ) -> ProbeCoverageResult: ...


class DataContractBuilderPort(Protocol):
    def build(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        variable_bindings: list[VariableBinding],
        probe_coverage: ProbeCoverageResult,
    ) -> DataContractBundle: ...


class Phase1OrchestratorPort(Protocol):
    def run_feasibility(
        self,
        state: ResearchState,
        *,
        config: RunnableConfig | None = None,
    ) -> ResearchState: ...


class Phase2OrchestratorPort(Protocol):
    def run_modeling(self, state: ResearchState) -> ResearchState: ...


class Phase3OrchestratorPort(Protocol):
    def run_execution(self, state: ResearchState) -> ResearchState: ...


__all__ = [
    "CsmarMetadataProviderPort",
    "DataContractBuilderPort",
    "Phase1OrchestratorPort",
    "Phase2OrchestratorPort",
    "Phase3OrchestratorPort",
    "ProbeExecutorPort",
    "RequirementParserPort",
    "VariableMapperPort",
    "VariableRequirementsBuilderPort",
]

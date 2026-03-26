from typing import Protocol

from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.mapping.ports import CsmarMetadataProviderPort
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.domains.spec.types import VariableRequirementsResult


class RequirementParserPort(Protocol):
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        ...


class VariableRequirementsBuilderPort(Protocol):
    def build(self, spec: ResearchSpec) -> VariableRequirementsResult:
        ...


class VariableMapperPort(Protocol):
    def map_probe_bindings(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingResult:
        ...


class ProbeExecutorPort(Protocol):
    def execute_coverage(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> ProbeCoverageResult:
        ...


class DataContractBuilderPort(Protocol):
    def build(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        variable_bindings: list[VariableBinding],
        probe_coverage: ProbeCoverageResult,
    ) -> DataContractBundle:
        ...


__all__ = [
    "CsmarMetadataProviderPort",
    "DataContractBuilderPort",
    "ProbeExecutorPort",
    "RequirementParserPort",
    "VariableMapperPort",
    "VariableRequirementsBuilderPort",
]

from typing import Protocol

from stata_agent.domains.contract.types import DataContractBundle
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.services.probe.contracts import ProbeCoverageResult


class DataContractBuilderPort(Protocol):
    def build(
        self,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        variable_bindings: list[VariableBinding],
        probe_coverage: ProbeCoverageResult,
    ) -> DataContractBundle: ...

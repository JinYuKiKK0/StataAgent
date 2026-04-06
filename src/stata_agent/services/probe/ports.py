from typing import Protocol

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.probe.contracts import ProbeCoverageResult
from stata_agent.services.probe.contracts import VariableProbeResult


class ProbeExecutorPort(Protocol):
    def run_field_probes(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> list[VariableProbeResult]: ...

    def drain_tool_traces(self) -> list[object]: ...


class ProbeCoverageSummarizerPort(Protocol):
    def summarize_coverage(
        self,
        spec: ResearchSpec,
        probe_results: list[VariableProbeResult],
    ) -> ProbeCoverageResult: ...

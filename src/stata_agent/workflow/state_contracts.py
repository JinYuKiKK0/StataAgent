from __future__ import annotations

from typing import TypeAlias, TypedDict

from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.fetch.types import VariableProbeResult
from stata_agent.domains.mapping.types import CsmarToolTrace
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingPlanResult
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.spec.types import DataRequirementsDraft
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.workflow.observability import WorkflowNodeAudit
from stata_agent.workflow.types import RunStage

NodeAuditMap: TypeAlias = dict[str, WorkflowNodeAudit]


class Phase1StateUpdate(TypedDict, total=False):
    spec: ResearchSpec
    parse_result: RequirementParseResult
    variable_definitions: list[VariableDefinition]
    data_requirements_draft: DataRequirementsDraft
    mapping_plan_result: VariableMappingPlanResult
    variable_bindings: list[VariableBinding]
    variable_mapping_result: VariableMappingResult
    probe_results_raw: list[VariableProbeResult]
    probe_coverage_result: ProbeCoverageResult
    data_contract_bundle: DataContractBundle
    csmar_traces: list[CsmarToolTrace]
    node_audits: NodeAuditMap
    notes: list[str]
    stage: RunStage

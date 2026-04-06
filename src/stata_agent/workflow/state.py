from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import GatewayRecord
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.fetch.types import VariableProbeResult
from stata_agent.domains.mapping.types import CsmarToolTrace
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingPlanResult
from stata_agent.domains.mapping.types import VariableMappingResult
from pydantic import BaseModel, Field

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import DataRequirementsDraft
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.workflow.state_contracts import NodeAuditMap
from stata_agent.workflow.types import RunStage


def _empty_csmar_traces() -> list[CsmarToolTrace]:
    return []


def _empty_node_audits() -> NodeAuditMap:
    return {}


class ResearchState(BaseModel):
    request: ResearchRequest
    stage: RunStage = RunStage.REQUESTED
    spec: ResearchSpec | None = None
    parse_result: RequirementParseResult | None = None
    variable_definitions: list[VariableDefinition] | None = None
    data_requirements_draft: DataRequirementsDraft | None = None
    mapping_plan_result: VariableMappingPlanResult | None = None
    variable_bindings: list[VariableBinding] | None = None
    variable_mapping_result: VariableMappingResult | None = None
    probe_results_raw: list[VariableProbeResult] | None = None
    probe_coverage_result: ProbeCoverageResult | None = None
    data_contract_bundle: DataContractBundle | None = None
    gateway_record: GatewayRecord | None = None
    csmar_traces: list[CsmarToolTrace] = Field(default_factory=_empty_csmar_traces)
    node_audits: NodeAuditMap = Field(default_factory=_empty_node_audits)
    notes: list[str] = Field(default_factory=list)

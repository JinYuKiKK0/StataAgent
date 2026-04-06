from pydantic import BaseModel, Field

from stata_agent.domains.contract.types import DataContractBundle
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.services.probe.contracts import ProbeCoverageResult
from stata_agent.services.spec.contracts import DataRequirementsDraft
from stata_agent.workflow.gateway import GatewayState
from stata_agent.workflow.observability import WorkflowNodeAudit
from stata_agent.workflow.types import RunStage

class Phase1Artifacts(BaseModel):
    spec: ResearchSpec | None = None
    variable_definitions: list[VariableDefinition] | None = None
    data_requirements_draft: DataRequirementsDraft | None = None
    variable_bindings: list[VariableBinding] | None = None
    probe_coverage_result: ProbeCoverageResult | None = None
    data_contract_bundle: DataContractBundle | None = None


class WorkflowAuditState(BaseModel):
    node_audits: dict[str, WorkflowNodeAudit] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ResearchState(BaseModel):
    request: ResearchRequest
    stage: RunStage = RunStage.REQUESTED
    phase1_artifacts: Phase1Artifacts = Field(default_factory=Phase1Artifacts)
    workflow_audit: WorkflowAuditState = Field(default_factory=WorkflowAuditState)
    gateway_state: GatewayState = Field(default_factory=GatewayState)

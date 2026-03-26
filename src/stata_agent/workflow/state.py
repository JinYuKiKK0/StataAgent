from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import GatewayRecord
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingResult
from pydantic import BaseModel, Field

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import DataRequirementsDraft
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.workflow.types import RunStage


class ResearchState(BaseModel):
    request: ResearchRequest
    stage: RunStage = RunStage.REQUESTED
    spec: ResearchSpec | None = None
    parse_result: RequirementParseResult | None = None
    variable_definitions: list[VariableDefinition] | None = None
    data_requirements_draft: DataRequirementsDraft | None = None
    variable_bindings: list[VariableBinding] | None = None
    variable_mapping_result: VariableMappingResult | None = None
    probe_coverage_result: ProbeCoverageResult | None = None
    data_contract_bundle: DataContractBundle | None = None
    gateway_record: GatewayRecord | None = None
    notes: list[str] = Field(default_factory=list)

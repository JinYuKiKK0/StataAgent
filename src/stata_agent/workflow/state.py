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
    notes: list[str] = Field(default_factory=list)

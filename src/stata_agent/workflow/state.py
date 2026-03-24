from pydantic import BaseModel, Field

from stata_agent.domain.enums import RunStage
from stata_agent.domain.models import ResearchRequest, ResearchSpec


class ResearchState(BaseModel):
    request: ResearchRequest
    stage: RunStage = RunStage.REQUESTED
    spec: ResearchSpec | None = None
    notes: list[str] = Field(default_factory=list)

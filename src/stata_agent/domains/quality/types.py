from pydantic import BaseModel, Field


class QualityDecision(BaseModel):
    passed: bool
    reasons: list[str] = Field(default_factory=list)

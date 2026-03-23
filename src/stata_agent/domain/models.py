from pathlib import Path

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str
    empirical_requirements: str
    entity_scope: str | None = None
    time_range: str | None = None
    granularity_hint: str | None = None
    output_preferences: list[str] = Field(default_factory=list)


class ResearchSpec(BaseModel):
    topic: str
    dependent_variable: str | None = None
    independent_variables: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    analysis_grain: str | None = None


class VariableBinding(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    confidence: float


class QueryPlan(BaseModel):
    table_name: str
    columns: list[str] = Field(default_factory=list)
    condition: str | None = None


class ResearchBundle(BaseModel):
    run_id: str
    spec: ResearchSpec | None = None
    dataset_path: Path | None = None
    artifacts: list[Path] = Field(default_factory=list)


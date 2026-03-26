from pydantic import BaseModel, Field


class QueryPlan(BaseModel):
    table_name: str
    columns: list[str] = Field(default_factory=list)
    condition: str | None = None


class VariableProbeResult(BaseModel):
    variable_name: str
    contract_tier: str = Field(default="soft", description="hard/soft")
    table_name: str
    field_name: str
    field_exists: bool
    frequency_match: bool
    query_count: int | None = None
    is_accessible: bool = False
    failure_reason: str | None = None


class ProbeCoverageResult(BaseModel):
    probe_results: list[VariableProbeResult] = Field(default_factory=list)
    hard_coverage_rate: float = 0.0
    soft_coverage_rate: float = 0.0
    hard_gaps: list[str] = Field(default_factory=list)
    soft_gaps: list[str] = Field(default_factory=list)
    key_alignment_ready: bool = False
    target_grain_ready: bool = False
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None

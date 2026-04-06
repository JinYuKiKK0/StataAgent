from pydantic import BaseModel, Field


class ProbeCoverageSummary(BaseModel):
    hard_coverage_rate: float = 0.0
    soft_coverage_rate: float = 0.0
    hard_gaps: list[str] = Field(default_factory=list)
    soft_gaps: list[str] = Field(default_factory=list)
    key_alignment_ready: bool = False
    target_grain_ready: bool = False
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None

class DataContractBundle(BaseModel):
    hard_contract_variables: list[str] = Field(default_factory=list)
    soft_contract_variables: list[str] = Field(default_factory=list)
    allowed_soft_removals: list[str] = Field(default_factory=list)
    analysis_grain: str = ""
    entity_scope: str
    entity_scope_inferred: bool = False
    time_start_year: int
    time_end_year: int
    empirical_requirements: str
    probe_coverage: ProbeCoverageSummary
    substitution_log: list[str] = Field(default_factory=list)
    residual_risks: list[str] = Field(default_factory=list)

from pydantic import BaseModel, Field


class VariableProbeResult(BaseModel):
    variable_name: str
    contract_tier: str = Field(default="soft", description="hard/soft")
    table_code: str
    field_name: str
    field_exists: bool
    frequency_match: bool
    query_count: int | None = None
    is_accessible: bool = False
    failure_reason: str | None = None
    trace_id: str = ""
    query_fingerprint: str = ""
    validation_id: str = ""
    scope_level: str = Field(default="time_scoped", description="探针范围")
    vendor_message: str = ""
    error_code: str = ""
    hint: str = ""
    retry_after_seconds: int | None = None
    suggested_args_patch: dict[str, object] | None = None


def _empty_probe_results() -> list[VariableProbeResult]:
    return []


class ProbeCoverageResult(BaseModel):
    probe_results: list[VariableProbeResult] = Field(
        default_factory=_empty_probe_results
    )
    hard_coverage_rate: float = 0.0
    soft_coverage_rate: float = 0.0
    hard_gaps: list[str] = Field(default_factory=list)
    soft_gaps: list[str] = Field(default_factory=list)
    key_alignment_ready: bool = False
    target_grain_ready: bool = False
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None

from pydantic import BaseModel, Field

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition


class ContractProbeResult(BaseModel):
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


def _empty_probe_results() -> list[ContractProbeResult]:
    return []


class ProbeCoverageSummary(BaseModel):
    probe_results: list[ContractProbeResult] = Field(
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


def _empty_variable_definitions() -> list[VariableDefinition]:
    return []


def _empty_variable_bindings() -> list[VariableBinding]:
    return []


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
    variable_definitions: list[VariableDefinition] = Field(
        default_factory=_empty_variable_definitions
    )
    variable_bindings: list[VariableBinding] = Field(
        default_factory=_empty_variable_bindings
    )
    probe_coverage: ProbeCoverageSummary
    substitution_log: list[str] = Field(default_factory=list)
    residual_risks: list[str] = Field(default_factory=list)
    spec: ResearchSpec

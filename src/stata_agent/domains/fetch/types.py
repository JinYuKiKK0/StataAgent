from enum import Enum

from pydantic import BaseModel, Field

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition


class QueryPlan(BaseModel):
    table_code: str
    columns: list[str] = Field(default_factory=list)
    condition: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    expected_grain: str = ""


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
    time_start_year: int
    time_end_year: int
    empirical_requirements: str
    variable_definitions: list[VariableDefinition] = Field(
        default_factory=_empty_variable_definitions
    )
    variable_bindings: list[VariableBinding] = Field(
        default_factory=_empty_variable_bindings
    )
    probe_coverage: ProbeCoverageResult
    substitution_log: list[str] = Field(default_factory=list)
    residual_risks: list[str] = Field(default_factory=list)
    spec: ResearchSpec


class GatewayDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class GatewayRecord(BaseModel):
    """Gateway 审批决策记录，持久化到 ResearchState。"""

    decision: GatewayDecision
    reason: str = ""


class GatewayResumeRequest(BaseModel):
    """Gateway 恢复请求契约。"""

    decision: GatewayDecision = GatewayDecision.REJECTED
    reason: str = ""

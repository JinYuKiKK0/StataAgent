from pydantic import BaseModel, Field

from stata_agent.domains.spec.types import VariableDefinition


class CsmarFieldSearchRequest(BaseModel):
    variable_name: str
    topic: str
    entity_scope: str
    analysis_grain_candidates: list[str] = Field(default_factory=list)
    time_start_year: int
    time_end_year: int
    candidate_limit: int = 12


class CsmarFieldCandidate(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    csmar_database: str
    alias_hit: bool = False
    table_label: str = ""
    field_label: str = ""
    field_description: str = ""
    aliases: list[str] = Field(default_factory=list)
    match_evidence: list[str] = Field(default_factory=list)
    frequency_tags: list[str] = Field(default_factory=list)
    catalog_source: str = Field(default="sdk_catalog", description="候选来源")


class VariableMatchDecision(BaseModel):
    matched: bool = False
    selected_table_name: str = ""
    selected_field_name: str = ""
    confidence: float = 0.0
    rationale: str = ""
    resolved_domain: str = ""


class CsmarFieldProbeRequest(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    contract_tier: str = Field(default="soft", description="hard/soft")
    entity_scope: str
    analysis_grain: str = ""
    time_start_year: int
    time_end_year: int


class CsmarFieldProbeResult(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    field_exists: bool
    row_count: int | None = None
    query_fingerprint: str = ""
    scope_level: str = Field(default="time_scoped", description="global/time_scoped")
    vendor_message: str = ""
    retriable: bool = False
    frequency_tags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VariableBinding(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    confidence: float
    csmar_database: str = ""
    contract_tier: str = Field(default="soft", description="hard/soft")
    is_hard_contract: bool = False
    frequency_match: bool = False
    source: str = Field(default="metadata_probe", description="映射来源")
    evidence: str = Field(default="", description="映射依据摘要")
    substituted_from: str | None = None
    table_label: str = ""
    field_label: str = ""


def _empty_bindings() -> list[VariableBinding]:
    return []


def _empty_variable_definitions() -> list[VariableDefinition]:
    return []


class VariableMappingResult(BaseModel):
    bindings: list[VariableBinding] = Field(default_factory=_empty_bindings)
    failure_reason: str | None = None
    hard_contract_variables: list[str] = Field(default_factory=list)
    soft_contract_gaps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    resolved_variable_definitions: list[VariableDefinition] = Field(
        default_factory=_empty_variable_definitions
    )

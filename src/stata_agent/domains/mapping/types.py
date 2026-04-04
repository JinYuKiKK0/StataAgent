from pydantic import BaseModel, Field

from stata_agent.domains.spec.types import VariableDefinition


class VariableMappingBudget(BaseModel):
    search_tables_limit: int = 1
    schema_reads_limit: int = 2
    search_fields_limit: int = 1
    enable_aux_field_search: bool = True


class CsmarTableSearchRequest(BaseModel):
    query: str
    database_name: str | None = None
    limit: int = 5


class CsmarTableCandidate(BaseModel):
    table_code: str
    table_name: str = ""
    database_name: str = ""
    score: float = 0.0
    why_matched: str = ""


class CsmarSchemaField(BaseModel):
    field_name: str
    field_label: str = ""
    field_description: str = ""
    data_type: str = ""
    frequency_tags: list[str] = Field(default_factory=list)
    role_tags: list[str] = Field(default_factory=list)


def _empty_schema_fields() -> list[CsmarSchemaField]:
    return []


class CsmarTableSchema(BaseModel):
    table_code: str
    table_name: str = ""
    database_name: str = ""
    fields: list[CsmarSchemaField] = Field(default_factory=_empty_schema_fields)


class CsmarFieldSearchRequest(BaseModel):
    query: str
    database_name: str | None = None
    table_code: str | None = None
    role_hint: str | None = None
    frequency_hint: str | None = None
    limit: int = 20


class CsmarFieldSearchHit(BaseModel):
    field_name: str
    field_label: str = ""
    field_description: str = ""
    data_type: str = ""
    frequency_tags: list[str] = Field(default_factory=list)
    role_tags: list[str] = Field(default_factory=list)
    table_code: str
    table_name: str = ""
    database_name: str = ""
    why_matched: str = ""
    score: float = 0.0


def _empty_object_rows() -> list[dict[str, object]]:
    return []


class CsmarProbeQueryResult(BaseModel):
    validation_id: str
    query_fingerprint: str
    row_count: int | None = None
    invalid_columns: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, object]] = Field(default_factory=_empty_object_rows)
    can_materialize: bool = True


class CsmarMaterializeAudit(BaseModel):
    retries: int
    packaged_at: str
    completed_at: str


class CsmarMaterializeQueryResult(BaseModel):
    download_id: str
    query_fingerprint: str
    output_dir: str
    files: list[str] = Field(default_factory=list)
    row_count: int
    archive_path: str
    audit: CsmarMaterializeAudit


class CsmarFieldCandidate(BaseModel):
    variable_name: str
    table_code: str
    field_name: str
    database_name: str
    alias_hit: bool = False
    table_name: str = ""
    table_label: str = ""
    field_label: str = ""
    field_description: str = ""
    aliases: list[str] = Field(default_factory=list)
    match_evidence: list[str] = Field(default_factory=list)
    frequency_tags: list[str] = Field(default_factory=list)
    catalog_source: str = Field(default="sdk_catalog", description="候选来源")


class VariableMatchDecision(BaseModel):
    matched: bool = False
    selected_table_code: str = ""
    selected_field_name: str = ""
    confidence: float = 0.0
    rationale: str = ""
    resolved_domain: str = ""


class CsmarFieldProbeRequest(BaseModel):
    variable_name: str
    table_code: str
    field_name: str
    contract_tier: str = Field(default="soft", description="hard/soft")
    entity_scope: str
    analysis_grain: str = ""
    time_start_year: int
    time_end_year: int


class CsmarFieldProbeResult(BaseModel):
    variable_name: str
    table_code: str
    field_name: str
    field_exists: bool
    row_count: int | None = None
    query_fingerprint: str = ""
    scope_level: str = Field(default="time_scoped", description="global/time_scoped")
    vendor_message: str = ""
    error_code: str = ""
    hint: str = ""
    retry_after_seconds: int | None = None
    suggested_args_patch: dict[str, object] | None = None
    retriable: bool = False
    frequency_tags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VariableBinding(BaseModel):
    variable_name: str
    table_code: str
    field_name: str
    confidence: float
    database_name: str = ""
    contract_tier: str = Field(default="soft", description="hard/soft")
    is_hard_contract: bool = False
    frequency_match: bool = False
    source: str = Field(default="metadata_probe", description="映射来源")
    evidence: str = Field(default="", description="映射依据摘要")
    substituted_from: str | None = None
    trace_id: str = ""
    table_name: str = ""
    table_label: str = ""
    field_label: str = ""


class CsmarToolTrace(BaseModel):
    trace_id: str
    tool_name: str
    request_payload: dict[str, object] = Field(default_factory=dict)
    result_summary: dict[str, object] | None = None
    error: dict[str, object] | None = None
    query_fingerprint: str | None = None
    validation_id: str | None = None
    cached: bool = False
    started_at: str
    completed_at: str


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

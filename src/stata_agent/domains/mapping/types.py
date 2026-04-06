from pydantic import BaseModel, Field

from stata_agent.domains.spec.types import VariableDefinition


class VariableMappingBudget(BaseModel):
    list_databases_limit: int = 1
    list_tables_limit: int = 4
    schema_reads_limit: int = 2
    max_total_calls: int = 12


class CsmarTableRecord(BaseModel):
    table_code: str
    table_name: str = ""
    database_name: str = ""


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
    validation_id: str = ""
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


class CsmarListDatabasesToolResult(BaseModel):
    ok: bool = True
    databases: list[str] = Field(default_factory=list)
    code: str = ""
    message: str = ""
    hint: str = ""
    trace_id: str = ""


def _empty_table_records() -> list[CsmarTableRecord]:
    return []


class CsmarListTablesToolResult(BaseModel):
    ok: bool = True
    database_name: str = ""
    items: list[CsmarTableRecord] = Field(default_factory=_empty_table_records)
    code: str = ""
    message: str = ""
    hint: str = ""
    trace_id: str = ""


def _empty_schema_result_fields() -> list[CsmarSchemaField]:
    return []


class CsmarGetTableSchemaToolResult(BaseModel):
    ok: bool = True
    table_code: str = ""
    table_name: str = ""
    database_name: str = ""
    fields: list[CsmarSchemaField] = Field(default_factory=_empty_schema_result_fields)
    code: str = ""
    message: str = ""
    hint: str = ""
    trace_id: str = ""


class VariableMappingPlanItem(BaseModel):
    variable_name: str
    matched: bool = False
    database_name: str = ""
    table_code: str = ""
    table_name: str = ""
    field_name: str = ""
    field_label: str = ""
    frequency_match: bool = False
    evidence: str = ""
    rationale: str = ""
    trace_id: str = ""


def _empty_mapping_plan_items() -> list[VariableMappingPlanItem]:
    return []


class VariableMappingPlanResult(BaseModel):
    items: list[VariableMappingPlanItem] = Field(default_factory=_empty_mapping_plan_items)
    failure_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)


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

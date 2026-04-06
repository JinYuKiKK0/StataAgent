from pydantic import BaseModel, Field

from stata_agent.domains.mapping.types import VariableBinding
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

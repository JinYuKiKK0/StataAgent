from pydantic import BaseModel, Field

from stata_agent.services.mapping.contracts import CsmarSchemaField
from stata_agent.services.mapping.contracts import CsmarTableRecord


def _empty_sample_rows() -> list[dict[str, object]]:
    return []


def _empty_table_records() -> list[CsmarTableRecord]:
    return []


def _empty_schema_fields() -> list[CsmarSchemaField]:
    return []


class CsmarProbeQueryResult(BaseModel):
    validation_id: str
    query_fingerprint: str
    row_count: int | None = None
    invalid_columns: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, object]] = Field(default_factory=_empty_sample_rows)
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


class CsmarListTablesToolResult(BaseModel):
    ok: bool = True
    database_name: str = ""
    items: list[CsmarTableRecord] = Field(default_factory=_empty_table_records)
    code: str = ""
    message: str = ""
    hint: str = ""
    trace_id: str = ""

class CsmarGetTableSchemaToolResult(BaseModel):
    ok: bool = True
    table_code: str = ""
    table_name: str = ""
    database_name: str = ""
    fields: list[CsmarSchemaField] = Field(default_factory=_empty_schema_fields)
    code: str = ""
    message: str = ""
    hint: str = ""
    trace_id: str = ""

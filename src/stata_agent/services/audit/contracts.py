from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    audit_ref: str
    kind: str
    payload: dict[str, object] = Field(default_factory=dict)


class TraceRecord(BaseModel):
    trace_ref: str
    payload: dict[str, object] = Field(default_factory=dict)

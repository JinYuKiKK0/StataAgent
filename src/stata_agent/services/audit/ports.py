from typing import Protocol

from stata_agent.services.audit.contracts import AuditRecord
from stata_agent.services.audit.contracts import TraceRecord


class AuditStorePort(Protocol):
    def write_audit(
        self,
        *,
        thread_id: str,
        kind: str,
        payload: dict[str, object],
    ) -> str: ...

    def read_audit(
        self,
        *,
        thread_id: str,
        audit_ref: str,
    ) -> AuditRecord | None: ...

    def write_traces(
        self,
        *,
        thread_id: str,
        traces: list[dict[str, object]],
    ) -> list[str]: ...

    def read_trace(
        self,
        *,
        thread_id: str,
        trace_ref: str,
    ) -> TraceRecord | None: ...

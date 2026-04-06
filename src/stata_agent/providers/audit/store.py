from __future__ import annotations

from collections.abc import Mapping
from typing import cast
from uuid import uuid4

from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from stata_agent.services.audit.contracts import AuditRecord
from stata_agent.services.audit.contracts import TraceRecord


class StoreBackedAuditStore:
    def __init__(self, store: BaseStore) -> None:
        self._store = store

    def write_audit(
        self,
        *,
        thread_id: str,
        kind: str,
        payload: dict[str, object],
    ) -> str:
        audit_ref = f"audit_{uuid4().hex[:12]}"
        self._store.put(
            self._audit_namespace(thread_id),
            audit_ref,
            {
                "kind": kind,
                "payload": payload,
            },
            index=False,
        )
        return audit_ref

    def read_audit(
        self,
        *,
        thread_id: str,
        audit_ref: str,
    ) -> AuditRecord | None:
        item = self._store.get(self._audit_namespace(thread_id), audit_ref)
        if item is None:
            return None
        value = item.value
        payload_value = value.get("payload")
        payload: dict[str, object] = {}
        if isinstance(payload_value, Mapping):
            payload_mapping = cast(Mapping[object, object], payload_value)
            for raw_key, raw_value in payload_mapping.items():
                payload[str(raw_key)] = raw_value
        return AuditRecord(
            audit_ref=audit_ref,
            kind=str(value.get("kind") or ""),
            payload=payload,
        )

    def write_traces(
        self,
        *,
        thread_id: str,
        traces: list[dict[str, object]],
    ) -> list[str]:
        refs: list[str] = []
        namespace = self._trace_namespace(thread_id)
        for trace in traces:
            trace_id = str(trace.get("trace_id") or "").strip()
            trace_ref = trace_id or f"trace_{uuid4().hex[:12]}"
            self._store.put(
                namespace,
                trace_ref,
                trace,
                index=False,
            )
            refs.append(trace_ref)
        return refs

    def read_trace(
        self,
        *,
        thread_id: str,
        trace_ref: str,
    ) -> TraceRecord | None:
        item = self._store.get(self._trace_namespace(thread_id), trace_ref)
        if item is None:
            return None
        value = item.value
        payload: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            payload[str(raw_key)] = cast(object, raw_value)
        return TraceRecord(
            trace_ref=trace_ref,
            payload=payload,
        )

    def _audit_namespace(self, thread_id: str) -> tuple[str, str]:
        return (thread_id, "audits")

    def _trace_namespace(self, thread_id: str) -> tuple[str, str]:
        return (thread_id, "traces")


class InMemoryAuditStore(StoreBackedAuditStore):
    def __init__(self) -> None:
        super().__init__(InMemoryStore())

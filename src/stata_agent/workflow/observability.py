from __future__ import annotations

from typing import cast

from pydantic import BaseModel, Field

from stata_agent.providers.csmar.types import CsmarToolTrace


class WorkflowNodeAudit(BaseModel):
    input_summary: dict[str, object] = Field(default_factory=dict)
    output_summary: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    trace_ids: list[str] = Field(default_factory=list)


def drain_component_traces(component: object) -> list[CsmarToolTrace]:
    drain = getattr(component, "drain_tool_traces", None)
    if not callable(drain):
        return []

    raw_traces_obj = drain()
    if not isinstance(raw_traces_obj, list):
        return []
    raw_traces = cast(list[object], raw_traces_obj)

    traces: list[CsmarToolTrace] = []
    for item in raw_traces:
        if isinstance(item, CsmarToolTrace):
            traces.append(item)
            continue
        try:
            traces.append(CsmarToolTrace.model_validate(item))
        except Exception:
            continue

    return traces


def merge_csmar_traces(
    existing: list[CsmarToolTrace],
    incoming: list[CsmarToolTrace],
) -> list[CsmarToolTrace]:
    merged_by_id: dict[str, CsmarToolTrace] = {}
    ordered_ids: list[str] = []
    for trace in [*existing, *incoming]:
        trace_id = trace.trace_id.strip()
        if not trace_id:
            continue
        if trace_id not in merged_by_id:
            merged_by_id[trace_id] = trace
            ordered_ids.append(trace_id)
            continue
        merged_by_id[trace_id] = _merge_trace_pair(merged_by_id[trace_id], trace)

    return [merged_by_id[trace_id] for trace_id in ordered_ids]


def collect_trace_ids(*trace_groups: list[CsmarToolTrace]) -> list[str]:
    trace_ids: list[str] = []
    seen: set[str] = set()
    for traces in trace_groups:
        for trace in traces:
            trace_id = trace.trace_id.strip()
            if not trace_id or trace_id in seen:
                continue
            trace_ids.append(trace_id)
            seen.add(trace_id)
    return trace_ids


def _merge_trace_pair(
    current: CsmarToolTrace,
    incoming: CsmarToolTrace,
) -> CsmarToolTrace:
    current_score = _trace_completeness_score(current)
    incoming_score = _trace_completeness_score(incoming)
    if incoming_score > current_score:
        preferred, fallback = incoming, current
    elif incoming_score < current_score:
        preferred, fallback = current, incoming
    elif incoming.completed_at > current.completed_at:
        preferred, fallback = incoming, current
    else:
        preferred, fallback = current, incoming

    return preferred.model_copy(
        update={
            "request_payload": preferred.request_payload or fallback.request_payload,
            "result_summary": preferred.result_summary or fallback.result_summary,
            "error": preferred.error or fallback.error,
            "query_fingerprint": preferred.query_fingerprint or fallback.query_fingerprint,
            "validation_id": preferred.validation_id or fallback.validation_id,
            "cached": preferred.cached or fallback.cached,
        }
    )


def _trace_completeness_score(trace: CsmarToolTrace) -> int:
    score = 0
    if trace.request_payload:
        score += 1
    if trace.result_summary:
        score += 2
    if trace.error:
        score += 2
    if trace.query_fingerprint:
        score += 1
    if trace.validation_id:
        score += 1
    if trace.cached:
        score += 1
    return score

from __future__ import annotations

from collections.abc import Sequence

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.providers.csmar.types import CsmarToolTrace
from stata_agent.services.probe.contracts import VariableProbeResult
from stata_agent.workflow.observability import WorkflowNodeAudit
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.state import WorkflowAuditState


def build_workflow_audit(
    state: ResearchState,
    *,
    notes: list[str],
    node_name: str,
    input_summary: dict[str, object],
    output_summary: dict[str, object],
    csmar_traces: Sequence[CsmarToolTrace] | None = None,
    warnings: list[str] | None = None,
    failure_reason: str | None = None,
    trace_ids: list[str] | None = None,
) -> WorkflowAuditState:
    audits = dict(state.workflow_audit.node_audits)
    audits[node_name] = WorkflowNodeAudit(
        input_summary=input_summary,
        output_summary=output_summary,
        warnings=warnings or [],
        failure_reason=failure_reason,
        trace_ids=trace_ids or [],
    )
    return state.workflow_audit.model_copy(
        update={
            "notes": notes,
            "node_audits": audits,
            "csmar_traces": (
                list(csmar_traces)
                if csmar_traces is not None
                else list(state.workflow_audit.csmar_traces)
            ),
        }
    )


def trace_ids_from_bindings(bindings: Sequence[VariableBinding]) -> list[str]:
    trace_ids: list[str] = []
    for binding in bindings:
        trace_id = binding.trace_id.strip()
        if trace_id and trace_id not in trace_ids:
            trace_ids.append(trace_id)
    return trace_ids


def trace_ids_from_probe_results(
    probe_results: Sequence[VariableProbeResult],
) -> list[str]:
    trace_ids: list[str] = []
    for result in probe_results:
        trace_id = result.trace_id.strip()
        if trace_id and trace_id not in trace_ids:
            trace_ids.append(trace_id)
    return trace_ids

from __future__ import annotations

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
    warnings: list[str] | None = None,
    failure_reason: str | None = None,
    audit_refs: list[str] | None = None,
    trace_refs: list[str] | None = None,
) -> WorkflowAuditState:
    audits = dict(state.workflow_audit.node_audits)
    audits[node_name] = WorkflowNodeAudit(
        input_summary=input_summary,
        output_summary=output_summary,
        warnings=warnings or [],
        failure_reason=failure_reason,
        audit_refs=audit_refs or [],
        trace_refs=trace_refs or [],
    )
    return state.workflow_audit.model_copy(
        update={
            "notes": notes,
            "node_audits": audits,
        }
    )

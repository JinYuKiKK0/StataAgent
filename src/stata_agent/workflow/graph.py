# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from collections.abc import Mapping
from typing import Literal, Protocol, cast

from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from stata_agent.workflow.gateway import GatewayDecision
from stata_agent.workflow.gateway import GatewayRecord
from stata_agent.workflow.gateway import GatewayResumeRequest
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.types import RunStage


class Phase1Node(Protocol):
    def __call__(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> ResearchState: ...


def gateway_approval_node(state: ResearchState) -> ResearchState:
    contract = state.phase1_artifacts.data_contract_bundle
    entity_scope_inferred = contract.entity_scope_inferred if contract else False
    message = "请审核最低可行数据契约并决定是否批准"
    if entity_scope_inferred:
        message = "请审核最低可行数据契约并决定是否批准（样本范围为 Agent 推断，请特别确认）"
    approval_payload = {
        "action": "gateway_approval",
        "message": message,
        "hard_contract_variables": contract.hard_contract_variables if contract else [],
        "soft_contract_variables": contract.soft_contract_variables if contract else [],
        "allowed_soft_removals": contract.allowed_soft_removals if contract else [],
        "residual_risks": contract.residual_risks if contract else [],
        "analysis_grain": contract.analysis_grain if contract else "",
        "entity_scope": contract.entity_scope if contract else "",
        "entity_scope_inferred": entity_scope_inferred,
        "time_range": f"{contract.time_start_year}-{contract.time_end_year}"
        if contract
        else "",
        "mapping_evidence_summary": _build_mapping_evidence_summary(state),
        "probe_trace_summary": _build_probe_trace_summary(state),
    }

    human_decision = cast(object, interrupt(approval_payload))
    resume_request = _coerce_gateway_resume_request(human_decision)
    return _apply_gateway_decision(state, resume_request)


def _build_mapping_evidence_summary(state: ResearchState) -> list[dict[str, str]]:
    contract = state.phase1_artifacts.data_contract_bundle
    if contract is None:
        return []

    return [
        {
            "variable_name": binding.variable_name,
            "table_code": binding.table_code,
            "field_name": binding.field_name,
            "trace_id": binding.trace_id,
            "evidence": binding.evidence,
        }
        for binding in contract.variable_bindings
    ]


def _build_probe_trace_summary(state: ResearchState) -> list[dict[str, str]]:
    contract = state.phase1_artifacts.data_contract_bundle
    if contract is None:
        return []

    trace_validation_map: dict[str, str] = {}
    for trace in state.workflow_audit.csmar_traces:
        trace_id = trace.trace_id.strip()
        validation_id = (trace.validation_id or "").strip()
        if trace_id and validation_id:
            trace_validation_map[trace_id] = validation_id

    summary: list[dict[str, str]] = []
    for result in contract.probe_coverage.probe_results:
        validation_id = result.validation_id.strip()
        if not validation_id:
            validation_id = trace_validation_map.get(result.trace_id.strip(), "")
        summary.append(
            {
                "variable_name": result.variable_name,
                "table_code": result.table_code,
                "field_name": result.field_name,
                "trace_id": result.trace_id,
                "query_fingerprint": result.query_fingerprint,
                "validation_id": validation_id,
                "error_code": result.error_code,
            }
        )
    return summary


def _coerce_gateway_resume_request(payload: object) -> GatewayResumeRequest:
    if not isinstance(payload, Mapping):
        return GatewayResumeRequest()

    decision_payload = cast(Mapping[str, object], payload)
    decision_raw = str(
        decision_payload.get("decision", GatewayDecision.REJECTED.value)
    )
    reason = str(decision_payload.get("reason", ""))

    try:
        decision = GatewayDecision(decision_raw)
    except ValueError:
        decision = GatewayDecision.REJECTED

    return GatewayResumeRequest(decision=decision, reason=reason)


def _apply_gateway_decision(
    state: ResearchState,
    decision_request: GatewayResumeRequest,
) -> ResearchState:
    record = GatewayRecord(
        decision=decision_request.decision,
        reason=decision_request.reason,
    )
    notes = list(state.workflow_audit.notes)
    gateway_state = state.gateway_state.model_copy(update={"record": record})
    if decision_request.decision is GatewayDecision.APPROVED:
        notes.append("Gateway 审批通过，数据契约已锁定。")
        return state.model_copy(
            update={
                "gateway_state": gateway_state,
                "stage": RunStage.APPROVED,
                "workflow_audit": state.workflow_audit.model_copy(update={"notes": notes}),
            }
        )

    notes.append(f"Gateway 审批被驳回：{decision_request.reason}")
    return state.model_copy(
        update={
            "gateway_state": gateway_state,
            "stage": RunStage.FAILED,
            "workflow_audit": state.workflow_audit.model_copy(update={"notes": notes}),
        }
    )


def route_after_phase1(
    state: ResearchState,
) -> Literal["gateway_approval", "__end__"]:
    if state.stage is RunStage.CONTRACTED:
        return "gateway_approval"
    return "__end__"


def build_workflow_graph(
    phase1_node: Phase1Node,
    *,
    checkpointer: BaseCheckpointSaver[str] | None = None,
):
    workflow = StateGraph(ResearchState)
    workflow.add_node("phase1_feasibility", phase1_node)
    workflow.add_node("gateway_approval", gateway_approval_node)

    workflow.add_edge(START, "phase1_feasibility")
    workflow.add_conditional_edges(
        "phase1_feasibility",
        route_after_phase1,
        ["gateway_approval", "__end__"],
    )
    workflow.add_edge("gateway_approval", END)

    if checkpointer is None:
        return workflow.compile()
    return workflow.compile(checkpointer=checkpointer)

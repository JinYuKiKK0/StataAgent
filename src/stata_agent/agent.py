"""LangGraph Agent 入口，供 LangSmith Agent Server 使用。

注意：LangGraph API 会自动处理持久化，因此这里导出的 graph 不包含 checkpointer。
"""

from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from stata_agent.domains.fetch.types import GatewayDecision, GatewayRecord
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator
from stata_agent.workflow.types import RunStage


def _run_phase1_node(state: ResearchState) -> ResearchState:
    return Phase1FeasibilityOrchestrator().run_feasibility(state)


def _gateway_approval_node(state: ResearchState) -> dict[str, Any]:
    """Gateway 审批中断与恢复。"""
    contract = state.data_contract_bundle
    approval_payload = {
        "action": "gateway_approval",
        "message": "请审核最低可行数据契约并决定是否批准",
        "hard_contract_variables": contract.hard_contract_variables
        if contract
        else [],
        "soft_contract_variables": contract.soft_contract_variables
        if contract
        else [],
        "allowed_soft_removals": contract.allowed_soft_removals if contract else [],
        "residual_risks": contract.residual_risks if contract else [],
        "analysis_grain": contract.analysis_grain if contract else "",
        "entity_scope": contract.entity_scope if contract else "",
        "time_range": f"{contract.time_start_year}-{contract.time_end_year}"
        if contract
        else "",
    }

    human_decision = interrupt(approval_payload)

    decision_data = (
        cast(dict[str, str], human_decision)
        if isinstance(human_decision, dict)
        else {}
    )
    decision_str: str = str(decision_data.get("decision", "rejected"))
    reason: str = str(decision_data.get("reason", ""))

    notes = list(state.notes)
    if decision_str == "approved":
        record = GatewayRecord(decision=GatewayDecision.APPROVED, reason=reason)
        notes.append("Gateway 审批通过，数据契约已锁定。")
        return {
            "gateway_record": record,
            "stage": RunStage.APPROVED,
            "notes": notes,
        }
    else:
        record = GatewayRecord(decision=GatewayDecision.REJECTED, reason=reason)
        notes.append(f"Gateway 审批被驳回：{reason}")
        return {
            "gateway_record": record,
            "stage": RunStage.FAILED,
            "notes": notes,
        }


def _route_after_phase1(
    state: ResearchState,
) -> Literal["gateway_approval", "__end__"]:
    if state.stage is RunStage.CONTRACTED:
        return "gateway_approval"
    return "__end__"


def _build_graph():
    workflow = StateGraph(ResearchState)
    workflow.add_node("phase1_feasibility", _run_phase1_node)
    workflow.add_node("gateway_approval", _gateway_approval_node)

    workflow.add_edge(START, "phase1_feasibility")
    workflow.add_conditional_edges(
        "phase1_feasibility",
        _route_after_phase1,
        ["gateway_approval", "__end__"],
    )
    workflow.add_edge("gateway_approval", END)

    return workflow.compile()


graph = _build_graph()

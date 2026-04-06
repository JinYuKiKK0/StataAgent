from typing import cast
from unittest.mock import patch

from stata_agent.domains.contract.types import DataContractBundle
from stata_agent.domains.contract.types import ProbeCoverageSummary
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.workflow.graph import gateway_approval_node
from stata_agent.workflow.gateway import GatewayDecision
from stata_agent.workflow.gateway import GatewayResumeRequest
from stata_agent.workflow.state import Phase1Artifacts
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.state import WorkflowAuditState
from stata_agent.workflow.types import RunStage


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行资本充足率与ROA",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_range="2018-2023",
        empirical_requirements="构建基准回归模型",
    )
def test_gateway_payload_only_contains_contract_summary() -> None:
    """验证 Gateway interrupt payload 只保留契约审批所需摘要，不含调试型映射/探针明细。"""
    contract = DataContractBundle(
        hard_contract_variables=["ROA", "资本充足率"],
        soft_contract_variables=[],
        allowed_soft_removals=[],
        analysis_grain="bank-year",
        entity_scope="A股上市银行",
        time_start_year=2018,
        time_end_year=2023,
        empirical_requirements="构建基准回归模型",
        probe_coverage=ProbeCoverageSummary(),
        residual_risks=[],
    )
    state = ResearchState(
        request=_build_request(),
        stage=RunStage.CONTRACTED,
        phase1_artifacts=Phase1Artifacts(data_contract_bundle=contract),
        workflow_audit=WorkflowAuditState(),
    )

    captured: dict[str, object] = {}

    approved = GatewayResumeRequest(
        decision=GatewayDecision.APPROVED,
        reason="",
    )

    def _fake_interrupt(payload: object) -> GatewayResumeRequest:
        if isinstance(payload, dict):
            captured.update(cast(dict[str, object], payload))
        return approved

    with (
        patch("stata_agent.workflow.graph.interrupt", side_effect=_fake_interrupt),
        patch("stata_agent.workflow.graph._coerce_gateway_resume_request", return_value=approved),
    ):
        resumed = gateway_approval_node(state)

    assert resumed.stage is RunStage.APPROVED
    assert "mapping_evidence_summary" not in captured
    assert "probe_trace_summary" not in captured
    assert captured["analysis_grain"] == "bank-year"
    assert captured["hard_contract_variables"] == ["ROA", "资本充足率"]

"""Gateway 审批载荷摘要测试。"""

from unittest.mock import patch
from typing import cast

from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import GatewayDecision
from stata_agent.domains.fetch.types import GatewayResumeRequest
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.fetch.types import VariableProbeResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.workflow.graph import gateway_approval_node
from stata_agent.workflow.state import ResearchState
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


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="银行资本充足率与ROA",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_start_year=2018,
        time_end_year=2023,
        control_variable_candidates=[],
        analysis_grain_candidates=["bank-year"],
    )


def test_gateway_payload_includes_mapping_and_probe_summaries() -> None:
    """验证 Gateway interrupt payload 含 evidence 摘要、trace_id 与 query_fingerprint 引用。"""
    binding = VariableBinding(
        variable_name="ROA",
        table_code="BANK_Index",
        field_name="ROAA",
        confidence=0.92,
        database_name="银行财务",
        contract_tier="hard",
        is_hard_contract=True,
        frequency_match=True,
        source="csmar_metadata_probe",
        evidence="alias命中=是; frequency匹配=是",
        trace_id="trace_bind_001",
        table_name="银行指标",
    )
    probe_result = VariableProbeResult(
        variable_name="ROA",
        contract_tier="hard",
        table_code="BANK_Index",
        field_name="ROAA",
        field_exists=True,
        frequency_match=True,
        query_count=128,
        is_accessible=True,
        trace_id="trace_probe_001",
        query_fingerprint="fingerprint_001",
        scope_level="time_scoped",
    )
    coverage = ProbeCoverageResult(
        probe_results=[probe_result],
        hard_coverage_rate=1.0,
        soft_coverage_rate=1.0,
        key_alignment_ready=True,
        target_grain_ready=True,
    )
    contract = DataContractBundle(
        hard_contract_variables=["ROA", "资本充足率"],
        soft_contract_variables=[],
        allowed_soft_removals=[],
        analysis_grain="bank-year",
        entity_scope="A股上市银行",
        time_start_year=2018,
        time_end_year=2023,
        empirical_requirements="构建基准回归模型",
        variable_bindings=[binding],
        probe_coverage=coverage,
        residual_risks=[],
        spec=_build_spec(),
    )
    state = ResearchState(
        request=_build_request(),
        stage=RunStage.CONTRACTED,
        data_contract_bundle=contract,
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
    assert "mapping_evidence_summary" in captured
    assert "probe_trace_summary" in captured

    mapping_summary = captured["mapping_evidence_summary"]
    assert isinstance(mapping_summary, list)
    assert mapping_summary
    assert mapping_summary[0]["trace_id"] == "trace_bind_001"

    probe_summary = captured["probe_trace_summary"]
    assert isinstance(probe_summary, list)
    assert probe_summary
    assert probe_summary[0]["query_fingerprint"] == "fingerprint_001"
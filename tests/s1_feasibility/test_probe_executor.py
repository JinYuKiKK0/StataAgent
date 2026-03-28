"""S1-T5 探针执行与覆盖摘要真实接口集成测试。"""

import pytest

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.services.probe_executor import ProbeExecutor
from stata_agent.services.requirement_parser import RequirementParser

pytest_plugins = ["tests.live_api_support"]

pytestmark = pytest.mark.live_api


def _build_hard_invalid_binding() -> VariableBinding:
    return VariableBinding(
        variable_name="硬约束不存在字段",
        table_name="FS_Comins",
        field_name="NOT_A_REAL_FIELD",
        confidence=0.1,
        csmar_database="财务报表",
        contract_tier="hard",
        is_hard_contract=True,
        frequency_match=True,
        source="live-test",
        evidence="hard-gap",
    )


def _build_soft_invalid_binding() -> VariableBinding:
    return VariableBinding(
        variable_name="软约束不存在字段",
        table_name="FS_Comins",
        field_name="NOT_A_REAL_FIELD_SOFT",
        confidence=0.1,
        csmar_database="财务报表",
        contract_tier="soft",
        is_hard_contract=False,
        frequency_match=True,
        source="live-test",
        evidence="soft-gap",
    )


def test_probe_executor_reports_real_coverage(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证探针节点会使用真实 CSMAR queryCount 返回覆盖摘要。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None

    executor = ProbeExecutor(metadata_provider=live_csmar_provider)
    hard_binding = VariableBinding(
        variable_name=live_request.dependent_variable,
        table_name="FS_Comins",
        field_name="ROA",
        confidence=0.9,
        csmar_database="财务报表",
        contract_tier="hard",
        is_hard_contract=True,
        frequency_match=True,
        source="live-test",
        evidence="real-csmar-querycount",
    )

    result = executor.execute_coverage(parse_result.spec, [hard_binding])

    assert result.failure_reason is None
    assert result.hard_coverage_rate == 1.0
    assert result.key_alignment_ready is True


def test_probe_executor_fails_fast_for_hard_gap(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证 Hard Contract 字段不可达时真实探针会触发 fail-fast。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None

    executor = ProbeExecutor(metadata_provider=live_csmar_provider)
    result = executor.execute_coverage(
        parse_result.spec,
        [_build_hard_invalid_binding()],
    )

    assert result.failure_reason is not None
    assert result.hard_gaps == ["硬约束不存在字段"]


def test_probe_executor_keeps_soft_gap_summary_without_abort(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证 Soft Contract 缺口只会被记录，真实探针仍允许继续。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None

    executor = ProbeExecutor(metadata_provider=live_csmar_provider)
    hard_binding = VariableBinding(
        variable_name=live_request.dependent_variable,
        table_name="FS_Comins",
        field_name="ROA",
        confidence=0.9,
        csmar_database="财务报表",
        contract_tier="hard",
        is_hard_contract=True,
        frequency_match=True,
        source="live-test",
        evidence="real-csmar-querycount",
    )

    result = executor.execute_coverage(
        parse_result.spec,
        [hard_binding, _build_soft_invalid_binding()],
    )

    assert result.failure_reason is None
    assert "软约束不存在字段" in result.soft_gaps

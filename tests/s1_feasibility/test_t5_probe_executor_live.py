"""S1-T5 探针执行 live API 测试。"""

import pytest

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.services.probe_executor import ProbeExecutor
from stata_agent.services.requirement_parser import RequirementParser

pytest_plugins = ["tests.live_api_support"]


def _build_hard_binding() -> VariableBinding:
    return VariableBinding(
        variable_name="ROA",
        table_code="FS_Comins",
        field_name="ROA",
        confidence=0.9,
        database_name="财务报表",
        contract_tier="hard",
        is_hard_contract=True,
        frequency_match=True,
        source="unit-test",
        evidence="hard",
        table_name="利润表",
    )


@pytest.mark.live_api
def test_probe_executor_reports_real_coverage(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证探针节点会使用真实 CSMAR queryCount 返回覆盖摘要。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None

    executor = ProbeExecutor(metadata_provider=live_csmar_provider)
    result = executor.execute_coverage(parse_result.spec, [_build_hard_binding()])

    assert result.failure_reason is None
    assert result.hard_coverage_rate == 1.0
    assert result.key_alignment_ready is True


@pytest.mark.live_api
def test_probe_executor_fails_fast_for_real_hard_gap(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证真实探针中 Hard Contract 字段不可达时会触发 fail-fast。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None

    executor = ProbeExecutor(metadata_provider=live_csmar_provider)
    invalid_binding = _build_hard_binding().model_copy(
        update={"field_name": "NOT_A_REAL_FIELD", "variable_name": "硬约束不存在字段"}
    )
    result = executor.execute_coverage(parse_result.spec, [invalid_binding])

    assert result.failure_reason is not None
    assert result.hard_gaps == ["硬约束不存在字段"]

"""S1-T5 探针执行 live API 测试。"""

import pytest

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.services.probe.contracts import ProbeExecutionInput
from stata_agent.services.probe.executor import ProbeExecutor
from stata_agent.services.probe.summarizer import ProbeCoverageSummarizer
from stata_agent.services.spec.requirement_parser import RequirementParser

pytest_plugins = ["tests.live_api_support"]


def _build_hard_binding() -> VariableBinding:
    return VariableBinding(
        variable_name="ROA",
        table_code="FS_Comins",
        field_name="ROA",
        contract_tier="hard",
        frequency_match=True,
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
    probe_results = executor.run_field_probes(
        ProbeExecutionInput(
            entity_scope=parse_result.spec.entity_scope,
            analysis_grain=parse_result.spec.analysis_grain_candidates[0],
            time_start_year=parse_result.spec.time_start_year,
            time_end_year=parse_result.spec.time_end_year,
            variable_bindings=[_build_hard_binding()],
        )
    )
    result = ProbeCoverageSummarizer().summarize_coverage(
        parse_result.spec, probe_results
    )

    assert result.failure_reason is None
    assert result.hard_coverage_rate == 1.0
    assert result.key_alignment_ready is True


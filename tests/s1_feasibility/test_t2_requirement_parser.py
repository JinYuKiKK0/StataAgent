"""S1-T2 需求解析真实接口集成测试。"""

import pytest

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.services.spec.requirement_parser import RequirementParser

pytest_plugins = ["tests.live_api_support"]

pytestmark = pytest.mark.live_api


def test_requirement_parser_calls_real_tongyi_and_returns_spec(
    live_parser: RequirementParser,
    live_request: ResearchRequest,
) -> None:
    """验证解析节点通过真实 Tongyi 调用后会产出可用 ResearchSpec。"""
    result = live_parser.parse(live_request)

    assert result.failure_reason is None
    assert result.spec is not None
    assert result.spec.analysis_grain_candidates
    assert result.spec.control_variable_candidates


def test_requirement_parser_keeps_user_hard_constraints(
    live_parser: RequirementParser,
    live_request: ResearchRequest,
) -> None:
    """验证真实模型输出会被校验并回填为用户提供的核心硬约束。"""
    result = live_parser.parse(live_request)

    assert result.spec is not None
    assert result.spec.dependent_variable == live_request.dependent_variable
    assert result.spec.independent_variables == live_request.independent_variables
    assert result.spec.entity_scope == live_request.entity_scope
    assert (
        result.spec.time_start_year == 2018 and result.spec.time_end_year == 2023
    )

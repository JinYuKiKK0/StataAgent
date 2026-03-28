# pyright: reportUnknownMemberType=false

"""LangGraph 共享入口真实接口集成测试。"""

import pytest
from typing import Any, cast

from stata_agent.agent import build_agent_graph
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.settings import Settings
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.types import RunStage

pytest_plugins = ["tests.live_api_support"]

pytestmark = pytest.mark.live_api


def test_agent_graph_interrupts_at_gateway_on_real_happy_path(
    live_settings: Settings,
    live_csmar_ready: None,
    live_request: ResearchRequest,
) -> None:
    """验证共享 graph 在真实路径上会命中 Gateway interrupt。"""
    graph = build_agent_graph()

    result = cast(
        dict[str, Any],
        graph.invoke(ResearchState(request=live_request), version="v1"),
    )

    assert result["stage"] is RunStage.CONTRACTED
    assert result["data_contract_bundle"] is not None
    assert "__interrupt__" in result
    assert result["__interrupt__"]


def test_agent_graph_returns_failed_state_when_real_mapping_fails(
    live_settings: Settings,
    live_csmar_ready: None,
    failing_live_request: ResearchRequest,
) -> None:
    """验证共享 graph 在真实 Hard Contract 映射失败时会返回 FAILED。"""
    graph = build_agent_graph()

    result = cast(
        dict[str, Any],
        graph.invoke(ResearchState(request=failing_live_request), version="v1"),
    )

    assert result["stage"] is RunStage.FAILED
    assert result["variable_mapping_result"] is not None

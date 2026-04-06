"""Phase 1 可行性编排真实接口集成测试。"""

import pytest

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator
from stata_agent.workflow.types import RunStage

pytest_plugins = ["tests.live_api_support"]

pytestmark = pytest.mark.live_api


def test_phase1_runs_to_contracted_state(
    live_phase1_orchestrator: Phase1FeasibilityOrchestrator,
    live_request: ResearchRequest,
) -> None:
    """验证真实 Phase 1 流水线会产出最低可行数据契约。"""
    state = live_phase1_orchestrator.run_feasibility(ResearchState(request=live_request))

    assert state.stage is RunStage.CONTRACTED
    assert state.phase1_artifacts.spec is not None
    assert state.phase1_artifacts.parse_result is not None
    assert state.phase1_artifacts.variable_definitions is not None
    assert state.phase1_artifacts.data_requirements_draft is not None
    assert state.phase1_artifacts.variable_bindings is not None
    assert state.phase1_artifacts.mapping_result is not None
    assert state.phase1_artifacts.probe_coverage_result is not None
    assert state.phase1_artifacts.data_contract_bundle is not None


def test_phase1_fails_when_hard_variable_cannot_be_mapped(
    live_phase1_orchestrator: Phase1FeasibilityOrchestrator,
    failing_live_request: ResearchRequest,
) -> None:
    """验证真实流程中 Hard Contract 映射失败会让编排进入失败态。"""
    state = live_phase1_orchestrator.run_feasibility(
        ResearchState(request=failing_live_request)
    )

    assert state.stage is RunStage.FAILED
    assert state.phase1_artifacts.mapping_result is not None
    assert state.phase1_artifacts.mapping_result.failure_reason is not None
    assert state.phase1_artifacts.variable_bindings is None

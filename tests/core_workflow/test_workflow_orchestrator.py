"""应用层工作流编排与 Gateway 恢复真实接口集成测试。"""

import pytest

from stata_agent.domains.fetch.types import GatewayDecision
from stata_agent.domains.fetch.types import GatewayResumeRequest
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.settings import Settings
from stata_agent.workflow.orchestrator import ApplicationOrchestrator
from stata_agent.workflow.types import RunStage

pytest_plugins = ["tests.live_api_support"]

pytestmark = pytest.mark.live_api


def test_orchestrator_happy_path_pauses_at_gateway(
    live_settings: Settings,
    live_csmar_ready: None,
    live_request: ResearchRequest,
) -> None:
    """验证真实工作流在完成 S1-T6 后会停在 Gateway 审批点。"""
    orchestrator = ApplicationOrchestrator()

    state, thread_id = orchestrator.run(live_request)

    assert state.stage is RunStage.CONTRACTED
    assert state.data_contract_bundle is not None
    assert thread_id.startswith("run-")


def test_gateway_approve_advances_to_approved_stage(
    live_settings: Settings,
    live_csmar_ready: None,
    live_request: ResearchRequest,
) -> None:
    """验证真实 Gateway 的 approve 路径会把状态推进到 APPROVED。"""
    orchestrator = ApplicationOrchestrator()

    state, thread_id = orchestrator.run(live_request)
    assert state.stage is RunStage.CONTRACTED

    resumed = orchestrator.resume(
        thread_id,
        GatewayResumeRequest(decision=GatewayDecision.APPROVED, reason=""),
    )

    assert resumed.stage is RunStage.APPROVED
    assert resumed.gateway_record is not None
    assert resumed.gateway_record.decision is GatewayDecision.APPROVED


def test_gateway_reject_fails_with_reason(
    live_settings: Settings,
    live_csmar_ready: None,
    live_request: ResearchRequest,
) -> None:
    """验证真实 Gateway 的 reject 路径会保留驳回原因并终止流程。"""
    orchestrator = ApplicationOrchestrator()

    state, thread_id = orchestrator.run(live_request)
    assert state.stage is RunStage.CONTRACTED

    resumed = orchestrator.resume(
        thread_id,
        GatewayResumeRequest(
            decision=GatewayDecision.REJECTED,
            reason="变量覆盖不满足预期",
        ),
    )

    assert resumed.stage is RunStage.FAILED
    assert resumed.gateway_record is not None
    assert resumed.gateway_record.decision is GatewayDecision.REJECTED
    assert resumed.gateway_record.reason == "变量覆盖不满足预期"


def test_orchestrator_fails_when_hard_mapping_is_unavailable(
    live_settings: Settings,
    live_csmar_ready: None,
    failing_live_request: ResearchRequest,
) -> None:
    """验证真实流程中 Hard Contract 变量不可映射时会在 Phase 1 失败。"""
    orchestrator = ApplicationOrchestrator()

    state, _ = orchestrator.run(failing_live_request)

    assert state.stage is RunStage.FAILED
    assert state.variable_mapping_result is not None
    assert state.variable_mapping_result.failure_reason is not None
    assert state.gateway_record is None

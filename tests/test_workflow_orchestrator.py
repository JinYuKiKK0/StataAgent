from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult, ResearchSpec
from stata_agent.providers.settings import Settings
from stata_agent.providers.settings import SettingsError
from stata_agent.workflow.orchestrator import ApplicationOrchestrator
from stata_agent.workflow.orchestrator import WorkflowBootstrapError
from stata_agent.workflow.types import RunStage


class SuccessfulParser:
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(
            spec=ResearchSpec(
                topic=request.topic,
                dependent_variable=request.dependent_variable,
                independent_variables=request.independent_variables,
                entity_scope=request.entity_scope,
                time_start_year=2010,
                time_end_year=2023,
                control_variable_candidates=["资产规模"],
                analysis_grain_candidates=["bank-year"],
            ),
            raw_response_text="ok",
        )


class FailingParser:
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(
            raw_response_text="bad output",
            failure_reason="需求解析失败：Tongyi 未产出可用的研究规范。",
        )


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_range="2010-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def test_orchestrator_runs_to_specified_state() -> None:
    orchestrator = ApplicationOrchestrator(parser=SuccessfulParser())

    state = orchestrator.run(_build_request())

    assert state.stage is RunStage.SPECIFIED
    assert state.spec is not None
    assert state.parse_result is not None
    assert "需求解析已完成。" in state.notes


def test_orchestrator_runs_to_failed_state() -> None:
    orchestrator = ApplicationOrchestrator(parser=FailingParser())

    state = orchestrator.run(_build_request())

    assert state.stage is RunStage.FAILED
    assert state.spec is None
    assert state.parse_result is not None
    assert "需求解析失败：Tongyi 未产出可用的研究规范。" in state.notes


def test_orchestrator_wraps_settings_errors() -> None:
    def failing_settings_factory() -> Settings:
        raise SettingsError(["DASHSCOPE_API_KEY: Field required"])

    orchestrator = ApplicationOrchestrator(settings_factory=failing_settings_factory)

    try:
        orchestrator.app_name()
    except WorkflowBootstrapError as exc:
        assert exc.details == ["DASHSCOPE_API_KEY: Field required"]
    else:
        raise AssertionError("Expected WorkflowBootstrapError to be raised")

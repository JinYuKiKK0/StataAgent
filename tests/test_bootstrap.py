from typer.testing import CliRunner

import pytest


def test_package_exposes_core_contracts() -> None:
    from stata_agent import __version__
    from stata_agent.domain.models import ResearchRequest
    from stata_agent.workflow.state import ResearchState

    request = ResearchRequest(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_range="2010-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )
    state = ResearchState(request=request)

    assert __version__ == "0.1.0"
    assert state.request == request


def test_cli_help_is_available() -> None:
    from stata_agent.cli import app

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "StataAgent" in result.stdout


def test_research_command_with_valid_input(monkeypatch: pytest.MonkeyPatch) -> None:
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.domain.enums import RunStage
    from stata_agent.domains.spec.types import RequirementParseResult, ResearchSpec
    from stata_agent.cli import app

    class SuccessfulOrchestrator:
        def run(self, request: ResearchRequest):
            from stata_agent.workflow.state import ResearchState

            return ResearchState(
                request=request,
                stage=RunStage.SPECIFIED,
                spec=ResearchSpec(
                    topic=request.topic,
                    dependent_variable=request.dependent_variable,
                    independent_variables=request.independent_variables,
                    entity_scope=request.entity_scope,
                    time_start_year=2010,
                    time_end_year=2023,
                    control_variable_candidates=["资产规模", "资本充足率"],
                    analysis_grain_candidates=["bank-year"],
                ),
                parse_result=RequirementParseResult(
                    raw_response_text="structured output",
                    warnings=["数字化口径需后续映射确认"],
                ),
            )

    monkeypatch.setattr("stata_agent.interfaces.cli.ApplicationOrchestrator", SuccessfulOrchestrator)
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic", "银行数字化转型与风险承担",
            "--y", "ROA",
            "--x", "数字化转型指数",
            "--entity", "A股上市银行",
            "--time", "2010-2023",
        ],
    )

    assert result.exit_code == 0
    assert "✓ 研究请求已完成需求解析" in result.stdout
    assert "银行数字化转型与风险承担" in result.stdout
    assert "ResearchSpec 摘要" in result.stdout
    assert "bank-year" in result.stdout
    assert "资产规模" in result.stdout


def test_research_command_with_parse_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.domain.enums import RunStage
    from stata_agent.domains.spec.types import RequirementParseResult
    from stata_agent.cli import app

    class FailingOrchestrator:
        def run(self, request: ResearchRequest):
            from stata_agent.workflow.state import ResearchState

            return ResearchState(
                request=request,
                stage=RunStage.FAILED,
                parse_result=RequirementParseResult(
                    raw_response_text="bad output",
                    failure_reason="需求解析失败：模型没有提供候选分析粒度。",
                ),
                notes=["需求解析失败：模型没有提供候选分析粒度。"],
            )

    monkeypatch.setattr("stata_agent.interfaces.cli.ApplicationOrchestrator", FailingOrchestrator)
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic", "银行数字化转型与风险承担",
            "--y", "ROA",
            "--x", "数字化转型指数",
            "--entity", "A股上市银行",
            "--time", "2010-2023",
        ],
    )

    assert result.exit_code == 1
    assert "需求解析阶段失败" in result.stdout
    assert "模型没有提供候选分析粒度" in result.stdout


def test_research_command_with_missing_tongyi_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from stata_agent.cli import app
    from stata_agent.providers.settings import get_settings

    monkeypatch.delenv("DASHSCOPE_API_KEY")
    get_settings.cache_clear()

    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic", "银行数字化转型与风险承担",
            "--y", "ROA",
            "--x", "数字化转型指数",
            "--entity", "A股上市银行",
            "--time", "2010-2023",
        ],
    )

    assert result.exit_code == 1
    assert "DASHSCOPE_API_KEY" in result.stdout


def test_research_command_missing_required_fields() -> None:
    from stata_agent.cli import app

    # 测试缺少 --topic
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--y", "ROA",
            "--x", "数字化转型指数",
            "--entity", "A股上市银行",
            "--time", "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--topic" in result.stderr or "Error" in result.stderr

    # 测试缺少 --y
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic", "银行数字化转型与风险承担",
            "--x", "数字化转型指数",
            "--entity", "A股上市银行",
            "--time", "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--y" in result.stderr or "Error" in result.stderr

    # 测试缺少 --x
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic", "银行数字化转型与风险承担",
            "--y", "ROA",
            "--entity", "A股上市银行",
            "--time", "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--x" in result.stderr or "Error" in result.stderr

    # 测试缺少 --entity
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic", "银行数字化转型与风险承担",
            "--y", "ROA",
            "--x", "数字化转型指数",
            "--time", "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--entity" in result.stderr or "Error" in result.stderr

    # 测试缺少 --time
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic", "银行数字化转型与风险承担",
            "--y", "ROA",
            "--x", "数字化转型指数",
            "--entity", "A股上市银行",
        ],
    )

    assert result.exit_code != 0
    assert "--time" in result.stderr or "Error" in result.stderr

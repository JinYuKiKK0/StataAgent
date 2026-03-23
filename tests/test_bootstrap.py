from typer.testing import CliRunner


def test_package_exposes_core_contracts() -> None:
    from stata_agent import __version__
    from stata_agent.domain.models import ResearchRequest
    from stata_agent.workflows.states import ResearchState

    request = ResearchRequest(
        topic="银行数字化转型与风险承担",
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


from typer.testing import CliRunner


def test_package_exposes_core_contracts() -> None:
    from stata_agent import __version__
    from stata_agent.domain.models import ResearchRequest
    from stata_agent.workflows.states import ResearchState

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


def test_research_command_with_valid_input() -> None:
    from stata_agent.cli import app

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
    assert "✓ 请求已接收并验证通过" in result.stdout
    assert "银行数字化转型与风险承担" in result.stdout
    assert "ROA" in result.stdout
    assert "数字化转型指数" in result.stdout


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


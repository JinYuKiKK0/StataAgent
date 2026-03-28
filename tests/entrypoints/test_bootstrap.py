"""包级启动与 CLI 入口测试。"""

from typer.testing import CliRunner

import pytest

from stata_agent.providers.settings import Settings

pytest_plugins = ["tests.live_api_support"]


def test_package_exposes_core_contracts() -> None:
    """验证安装后的顶层包仍暴露最小可用契约。"""
    from stata_agent import __version__
    from stata_agent.domains.request.types import ResearchRequest
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
    """验证 CLI 启动面正常，用户可见帮助与命令说明。"""
    from stata_agent.interfaces.cli import app

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "StataAgent" in result.stdout


@pytest.mark.live_api
def test_research_command_reports_real_mapping_failure(
    live_settings: Settings,
    live_csmar_ready: None,
) -> None:
    """验证 CLI 在真实链路中会透传映射失败，而不是依赖替身对象。"""
    from stata_agent.interfaces.cli import app

    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic",
            "银行资本充足率与盈利能力",
            "--y",
            "不存在的核心变量",
            "--x",
            "资本充足率",
            "--entity",
            "A股上市银行",
            "--time",
            "2018-2023",
        ],
    )

    assert live_settings.app_name == "StataAgent"
    assert result.exit_code == 1
    assert "变量映射失败" in result.stdout


def test_research_command_missing_required_fields() -> None:
    """验证 CLI 对研究请求必填字段做入口级校验。"""
    from stata_agent.interfaces.cli import app

    result = CliRunner().invoke(
        app,
        [
            "research",
            "--y",
            "ROA",
            "--x",
            "数字化转型指数",
            "--entity",
            "A股上市银行",
            "--time",
            "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--topic" in result.stderr or "Error" in result.stderr

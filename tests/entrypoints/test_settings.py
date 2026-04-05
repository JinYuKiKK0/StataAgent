"""Settings 配置契约测试。"""

from pathlib import Path

from stata_agent.providers import settings as settings_module
from stata_agent.providers.settings import Settings


def test_settings_have_stata_executor_mcp_defaults() -> None:
    """验证 Stata Executor MCP 启动字段具备稳定默认值。"""
    settings = Settings.model_validate(
        {
            "workspace_dir": Path("/tmp/stata-workspace"),
            "dashscope_api_key": "test-dashscope-key",
            "tongyi_model": "qwen-plus",
        }
    )

    assert settings.stata_executor_mcp_command == "uv"
    assert settings.stata_executor_mcp_args == [
        "run",
        "--package",
        "stata-executor",
        "stata-executor-mcp",
    ]
    assert settings.stata_executor_mcp_workdir is None


def test_settings_accept_stata_executor_mcp_aliases() -> None:
    """验证 STATA_EXECUTOR_* 环境别名可用于配置解析。"""
    settings = Settings.model_validate(
        {
            "workspace_dir": Path("/tmp/stata-workspace"),
            "dashscope_api_key": "test-dashscope-key",
            "tongyi_model": "qwen-plus",
            "STATA_EXECUTOR_MCP_COMMAND": "python",
            "STATA_EXECUTOR_MCP_ARGS": ["-m", "stata_executor.adapters.mcp"],
            "STATA_EXECUTOR_MCP_WORKDIR": "/opt/stata-executor",
        }
    )

    assert settings.stata_executor_mcp_command == "python"
    assert settings.stata_executor_mcp_args == ["-m", "stata_executor.adapters.mcp"]
    assert settings.stata_executor_mcp_workdir == Path("/opt/stata-executor")


def test_env_labels_include_stata_executor_mcp_keys() -> None:
    """验证设置错误映射表包含 Stata Executor MCP 三个变量。"""
    labels = settings_module._ENV_LABELS  # pyright: ignore[reportPrivateUsage]
    assert labels["stata_executor_mcp_command"] == "STATA_EXECUTOR_MCP_COMMAND"
    assert labels["stata_executor_mcp_args"] == "STATA_EXECUTOR_MCP_ARGS"
    assert labels["stata_executor_mcp_workdir"] == "STATA_EXECUTOR_MCP_WORKDIR"
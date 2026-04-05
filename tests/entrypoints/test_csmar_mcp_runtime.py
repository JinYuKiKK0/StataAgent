"""CSMAR MCP 启动参数构建测试。"""

from pathlib import Path

import pytest

from stata_agent.providers.csmar.mcp_runtime import build_csmar_mcp_launch_spec
from stata_agent.providers.settings import Settings


def _build_settings(**overrides: object) -> Settings:
    payload: dict[str, object] = {
        "workspace_dir": Path("/tmp/stata-workspace"),
        "dashscope_api_key": "test-dashscope-key",
        "tongyi_model": "qwen-plus",
        "csmar_account": "demo-account",
        "csmar_password": "demo-password",
    }
    payload.update(overrides)
    return Settings.model_validate(payload)


def test_build_launch_spec_uses_default_workdir_and_injected_credentials(
    tmp_path: Path,
) -> None:
    """验证默认配置会推导 monorepo MCP 目录并自动注入账号密码参数。"""
    repo_root = tmp_path / "repo"
    expected_workdir = repo_root / "packages" / "csmar-mcp"
    expected_workdir.mkdir(parents=True, exist_ok=True)
    settings = _build_settings(workspace_dir=repo_root / ".stata-agent")

    spec = build_csmar_mcp_launch_spec(settings)

    assert spec.command == "uv"
    assert spec.args == (
        "run",
        "--package",
        "csmar-mcp",
        "csmar-mcp",
        "--account",
        "demo-account",
        "--password",
        "demo-password",
    )
    assert spec.cwd == expected_workdir
    assert spec.start_timeout_seconds == 20
    assert spec.call_timeout_seconds == 120
    assert spec.env_overrides == {}


def test_build_launch_spec_respects_custom_mcp_configuration() -> None:
    """验证自定义 MCP 命令、参数、目录和状态路径会被完整保留。"""
    settings = _build_settings(
        csmar_mcp_command="python",
        csmar_mcp_args=["-m", "csmar_mcp"],
        csmar_mcp_workdir=Path("/opt/csmar-mcp"),
        csmar_mcp_state_dir=Path("/var/tmp/csmar-state"),
        csmar_mcp_start_timeout_seconds=45,
        csmar_mcp_call_timeout_seconds=300,
    )

    spec = build_csmar_mcp_launch_spec(settings)

    assert spec.command == "python"
    assert spec.args == (
        "-m",
        "csmar_mcp",
        "--account",
        "demo-account",
        "--password",
        "demo-password",
    )
    assert spec.cwd == Path("/opt/csmar-mcp")
    assert spec.start_timeout_seconds == 45
    assert spec.call_timeout_seconds == 300
    assert spec.env_overrides == {
        "CSMAR_MCP_STATE_DIR": str(Path("/var/tmp/csmar-state")),
    }


def test_build_launch_spec_requires_credentials() -> None:
    """验证缺少 CSMAR 凭证时会阻断 MCP 启动并返回明确错误。"""
    settings = _build_settings(csmar_account=None, csmar_password=None)

    with pytest.raises(ValueError, match="CSMAR_ACCOUNT"):
        build_csmar_mcp_launch_spec(settings)


def test_build_launch_spec_rejects_credential_flags_in_base_args() -> None:
    """验证基础参数中若手动包含凭证标记会被拒绝，避免冲突注入。"""
    settings = _build_settings(csmar_mcp_args=["run", "csmar-mcp", "--account", "x"])

    with pytest.raises(ValueError, match="CSMAR_MCP_ARGS"):
        build_csmar_mcp_launch_spec(settings)

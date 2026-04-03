from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stata_agent.providers.settings import Settings


@dataclass(frozen=True, slots=True)
class CsmarMcpLaunchSpec:
    command: str
    args: tuple[str, ...]
    cwd: Path
    start_timeout_seconds: int
    call_timeout_seconds: int
    env_overrides: dict[str, str]


def build_csmar_mcp_launch_spec(settings: Settings) -> CsmarMcpLaunchSpec:
    account = (settings.csmar_account or "").strip()
    password = ""
    if settings.csmar_password is not None:
        password = settings.csmar_password.get_secret_value().strip()

    if not account or not password:
        raise ValueError(
            "CSMAR MCP 启动失败：缺少 CSMAR_ACCOUNT 或 CSMAR_PASSWORD。"
        )

    base_args = tuple(settings.csmar_mcp_args)
    _assert_credential_flags_not_in_base_args(base_args)

    launch_args = (*base_args, "--account", account, "--password", password)
    env_overrides: dict[str, str] = {}
    if settings.csmar_mcp_state_dir is not None:
        env_overrides["CSMAR_MCP_STATE_DIR"] = str(
            settings.csmar_mcp_state_dir.expanduser().resolve()
        )

    return CsmarMcpLaunchSpec(
        command=settings.csmar_mcp_command,
        args=launch_args,
        cwd=resolve_csmar_mcp_workdir(settings),
        start_timeout_seconds=settings.csmar_mcp_start_timeout_seconds,
        call_timeout_seconds=settings.csmar_mcp_call_timeout_seconds,
        env_overrides=env_overrides,
    )


def resolve_csmar_mcp_workdir(settings: Settings) -> Path:
    if settings.csmar_mcp_workdir is not None:
        return settings.csmar_mcp_workdir.expanduser().resolve()
    return (settings.workspace_dir.expanduser().resolve().parent / "CSMAR-Data-MCP").resolve()


def _assert_credential_flags_not_in_base_args(args: tuple[str, ...]) -> None:
    for token in args:
        if token in {"--account", "--password"}:
            raise ValueError(
                "CSMAR_MCP_ARGS 不应包含 --account/--password；provider 会自动注入凭证。"
            )

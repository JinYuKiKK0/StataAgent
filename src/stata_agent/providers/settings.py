from functools import lru_cache
from pathlib import Path
from typing import cast

from pydantic import AliasChoices, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_LABELS = {
    "workspace_dir": "WORKSPACE_DIR",
    "dashscope_api_key": "DASHSCOPE_API_KEY",
    "tongyi_model": "TONGYI_MODEL",
    "csmar_account": "CSMAR_ACCOUNT",
    "csmar_password": "CSMAR_PASSWORD",
    "csmar_mcp_command": "CSMAR_MCP_COMMAND",
    "csmar_mcp_args": "CSMAR_MCP_ARGS",
    "csmar_mcp_workdir": "CSMAR_MCP_WORKDIR",
    "csmar_mcp_start_timeout_seconds": "CSMAR_MCP_START_TIMEOUT_SECONDS",
    "csmar_mcp_call_timeout_seconds": "CSMAR_MCP_CALL_TIMEOUT_SECONDS",
    "csmar_mcp_state_dir": "CSMAR_MCP_STATE_DIR",
    "stata_executor_mcp_command": "STATA_EXECUTOR_MCP_COMMAND",
    "stata_executor_mcp_args": "STATA_EXECUTOR_MCP_ARGS",
    "stata_executor_mcp_workdir": "STATA_EXECUTOR_MCP_WORKDIR",
}


class SettingsError(RuntimeError):
    def __init__(self, details: list[str]) -> None:
        super().__init__("配置环境校验失败")
        self.details = details


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="StataAgent", validation_alias=AliasChoices("APP_NAME", "app_name")
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "environment"),
    )
    workspace_dir: Path = Field(
        ...,
        description="工作空间文件目录",
        validation_alias=AliasChoices("WORKSPACE_DIR", "workspace_dir"),
    )
    dashscope_api_key: SecretStr = Field(
        ...,
        description="Tongyi DashScope API key",
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "dashscope_api_key"),
    )
    tongyi_model: str = Field(
        ...,
        description="Tongyi model name, e.g. qwen-plus",
        validation_alias=AliasChoices("TONGYI_MODEL", "tongyi_model"),
    )
    csmar_account: str | None = Field(
        default=None,
        description="CSMAR account, e.g. phone/email/username",
        validation_alias=AliasChoices("CSMAR_ACCOUNT", "csmar_account"),
    )
    csmar_password: SecretStr | None = Field(
        default=None,
        description="CSMAR account password",
        validation_alias=AliasChoices("CSMAR_PASSWORD", "csmar_password"),
    )
    csmar_language: int = Field(
        default=0,
        description="CSMAR language, 0 for zh-cn, 1 for en-us",
        validation_alias=AliasChoices("CSMAR_LANGUAGE", "csmar_language"),
    )
    csmar_mcp_command: str = Field(
        default="uv",
        description="Command used to launch CSMAR MCP server.",
        validation_alias=AliasChoices("CSMAR_MCP_COMMAND", "csmar_mcp_command"),
    )
    csmar_mcp_args: list[str] = Field(
        default_factory=lambda: ["run", "--package", "csmar-mcp", "csmar-mcp"],
        description="Base args for launching CSMAR MCP server (without credentials).",
        validation_alias=AliasChoices("CSMAR_MCP_ARGS", "csmar_mcp_args"),
    )
    csmar_mcp_workdir: Path | None = Field(
        default=None,
        description="Optional MCP working directory; defaults to packages/csmar-mcp in monorepo.",
        validation_alias=AliasChoices("CSMAR_MCP_WORKDIR", "csmar_mcp_workdir"),
    )
    csmar_mcp_start_timeout_seconds: int = Field(
        default=20,
        ge=1,
        description="MCP process start timeout in seconds.",
        validation_alias=AliasChoices(
            "CSMAR_MCP_START_TIMEOUT_SECONDS", "csmar_mcp_start_timeout_seconds"
        ),
    )
    csmar_mcp_call_timeout_seconds: int = Field(
        default=120,
        ge=1,
        description="MCP tool call timeout in seconds.",
        validation_alias=AliasChoices(
            "CSMAR_MCP_CALL_TIMEOUT_SECONDS", "csmar_mcp_call_timeout_seconds"
        ),
    )
    csmar_mcp_state_dir: Path | None = Field(
        default=None,
        description="Optional state directory passed to MCP runtime environment.",
        validation_alias=AliasChoices("CSMAR_MCP_STATE_DIR", "csmar_mcp_state_dir"),
    )
    stata_executor_mcp_command: str = Field(
        default="uv",
        description="Command used to launch Stata Executor MCP server.",
        validation_alias=AliasChoices(
            "STATA_EXECUTOR_MCP_COMMAND",
            "stata_executor_mcp_command",
        ),
    )
    stata_executor_mcp_args: list[str] = Field(
        default_factory=lambda: [
            "run",
            "--package",
            "stata-executor",
            "stata-executor-mcp",
        ],
        description="Base args for launching Stata Executor MCP server.",
        validation_alias=AliasChoices(
            "STATA_EXECUTOR_MCP_ARGS",
            "stata_executor_mcp_args",
        ),
    )
    stata_executor_mcp_workdir: Path | None = Field(
        default=None,
        description="Optional Stata Executor MCP working directory.",
        validation_alias=AliasChoices(
            "STATA_EXECUTOR_MCP_WORKDIR",
            "stata_executor_mcp_workdir",
        ),
    )

    @field_validator("csmar_mcp_command")
    @classmethod
    def validate_csmar_mcp_command(cls, value: str) -> str:
        command = value.strip()
        if not command:
            raise ValueError("command must not be empty")
        return command

    @field_validator("csmar_mcp_args")
    @classmethod
    def validate_csmar_mcp_args(cls, value: list[str]) -> list[str]:
        args = [item.strip() for item in value if item.strip()]
        if not args:
            raise ValueError("args must contain at least one non-empty argument")
        return args


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        return Settings()  # pyright: ignore[reportCallIssue]
    except ValidationError as e:
        details: list[str] = []
        for err in cast(list[dict[str, object]], e.errors()):
            field = str(cast(tuple[object, ...], err["loc"])[0])
            label = _ENV_LABELS.get(field, field)
            details.append(f"{label}: {err['msg']}")
        raise SettingsError(details) from e

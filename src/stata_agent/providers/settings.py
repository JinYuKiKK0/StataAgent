from functools import lru_cache
from pathlib import Path
from typing import cast

from pydantic import AliasChoices, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_LABELS = {
    "workspace_dir": "WORKSPACE_DIR",
    "dashscope_api_key": "DASHSCOPE_API_KEY",
    "tongyi_model": "TONGYI_MODEL",
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

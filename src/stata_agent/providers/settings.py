from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, Field, ValidationError


class SettingsError(RuntimeError):
    def __init__(self, details: list[str]) -> None:
        super().__init__("配置环境校验失败")
        self.details = details


class Settings(BaseModel):
    app_name: str = "StataAgent"
    environment: str = "development"
    workspace_dir: Path = Field(..., description="工作空间文件目录")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env_file = Path(".env")
    env_dict = dotenv_values(env_file) if env_file.exists() else {}
    env_data = {key: value for key, value in env_dict.items() if value is not None}

    try:
        return Settings.model_validate(env_data)
    except ValidationError as e:
        details = [str(err) for err in e.errors()]
        raise SettingsError(details) from e

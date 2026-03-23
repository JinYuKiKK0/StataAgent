from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StataAgent"
    environment: str = "development"
    workspace_dir: Path = Path(".stata-agent")

    model_config = SettingsConfigDict(
        env_prefix="STATA_AGENT_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


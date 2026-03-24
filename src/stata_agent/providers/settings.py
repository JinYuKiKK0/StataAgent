import sys
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, Field, ValidationError


class Settings(BaseModel):
    app_name: str = "StataAgent"
    environment: str = "development"
    workspace_dir: Path = Field(..., description="工作空间文件目录")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    from rich.console import Console

    console = Console()
    env_file = Path(".env")
    env_dict = dotenv_values(env_file) if env_file.exists() else {}
    env_data = {key: value for key, value in env_dict.items() if value is not None}

    try:
        return Settings.model_validate(env_data)
    except ValidationError as e:
        console.print("\n[bold red]✗ 配置层启动阻截：配置环境校验失败[/bold red]")
        console.print("[yellow]确保项目根目录下存在 `.env` 文件，且其包含如下受约束配置：[/yellow]")
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            msg = err["msg"]
            console.print(f"  - [cyan]{field}[/cyan]: {msg}")
        sys.exit(1)

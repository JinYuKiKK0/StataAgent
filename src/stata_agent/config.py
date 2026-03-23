import sys
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, Field, ValidationError

class Settings(BaseModel):
    app_name: str = "StataAgent"
    environment: str = "development"
    # 强制声明该字段为必须配置，不再给备用的硬编码默认值
    workspace_dir: Path = Field(..., description="工作空间文件目录")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    from rich.console import Console
    console = Console()
    
    env_file = Path(".env")
    # 基于.env物理文件读成字典数据源
    env_dict = dotenv_values(env_file) if env_file.exists() else {}
    
    try:
        # BaseModel 将严酷地对纯粹抽出来的 env_dict 检验其契约属性
        return Settings(**env_dict)
    except ValidationError as e:
        console.print("\n[bold red]✗ 配置层启动阻截：配置环境校验失败[/bold red]")
        console.print("[yellow]确保项目根目录下存在 `.env` 文件，且其包含如下受约束配置：[/yellow]")
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            msg = err["msg"]
            console.print(f"  - [cyan]{field}[/cyan]: {msg}")
        sys.exit(1)

from pathlib import Path

from pydantic import BaseModel, Field


class StataExecutionResult(BaseModel):
    log_path: Path
    artifacts: list[Path] = Field(default_factory=list)

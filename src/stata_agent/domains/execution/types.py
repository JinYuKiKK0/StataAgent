from pathlib import Path

from pydantic import BaseModel, Field


def _empty_artifact_paths() -> list[Path]:
    return []


class StataExecutionResult(BaseModel):
    log_path: Path
    artifacts: list[Path] = Field(default_factory=_empty_artifact_paths)

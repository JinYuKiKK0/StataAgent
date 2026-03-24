from pathlib import Path

from pydantic import BaseModel, Field


class StataRunPlan(BaseModel):
    do_file_path: Path
    dataset_path: Path
    arguments: list[str] = Field(default_factory=list)

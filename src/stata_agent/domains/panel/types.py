from pathlib import Path

from pydantic import BaseModel, Field


class PanelDataset(BaseModel):
    path: Path
    row_count: int = 0
    column_names: list[str] = Field(default_factory=list)

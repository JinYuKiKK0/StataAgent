from pathlib import Path

from pydantic import BaseModel, Field

from stata_agent.domains.spec.types import ResearchSpec


class ResearchBundle(BaseModel):
    run_id: str
    spec: ResearchSpec | None = None
    dataset_path: Path | None = None
    artifacts: list[Path] = Field(default_factory=list)

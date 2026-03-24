from pydantic import BaseModel, Field


class QueryPlan(BaseModel):
    table_name: str
    columns: list[str] = Field(default_factory=list)
    condition: str | None = None

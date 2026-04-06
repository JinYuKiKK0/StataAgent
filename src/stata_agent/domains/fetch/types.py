from pydantic import BaseModel, Field


class QueryPlan(BaseModel):
    table_code: str
    columns: list[str] = Field(default_factory=list)
    condition: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    expected_grain: str = ""

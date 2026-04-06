from pydantic import BaseModel, Field


class VariableBinding(BaseModel):
    variable_name: str
    table_code: str
    field_name: str
    contract_tier: str = Field(default="soft", description="hard/soft")
    frequency_match: bool = False
    substituted_from: str | None = None

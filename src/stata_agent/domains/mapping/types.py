from pydantic import BaseModel, Field


class VariableBinding(BaseModel):
    variable_name: str
    table_code: str
    field_name: str
    confidence: float
    database_name: str = ""
    contract_tier: str = Field(default="soft", description="hard/soft")
    is_hard_contract: bool = False
    frequency_match: bool = False
    source: str = Field(default="metadata_probe", description="映射来源")
    evidence: str = Field(default="", description="映射依据摘要")
    substituted_from: str | None = None
    trace_id: str = ""
    table_name: str = ""
    table_label: str = ""
    field_label: str = ""

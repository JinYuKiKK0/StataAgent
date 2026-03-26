from pydantic import BaseModel, Field


class VariableBinding(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    confidence: float
    csmar_database: str = ""
    contract_tier: str = Field(default="soft", description="hard/soft")
    is_hard_contract: bool = False
    frequency_match: bool = False
    source: str = Field(default="metadata_probe", description="映射来源")
    evidence: str = Field(default="", description="映射依据摘要")
    substituted_from: str | None = None


def _empty_bindings() -> list[VariableBinding]:
    return []


class VariableMappingResult(BaseModel):
    bindings: list[VariableBinding] = Field(default_factory=_empty_bindings)
    failure_reason: str | None = None
    hard_contract_variables: list[str] = Field(default_factory=list)
    soft_contract_gaps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CsmarFieldCandidate(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    csmar_database: str
    alias_hit: bool
    frequency_tags: list[str] = Field(default_factory=list)

from pydantic import BaseModel, Field


class ResearchSpec(BaseModel):
    topic: str = Field(..., description="解析后的研究主题")
    dependent_variable: str = Field(..., description="解析后的因变量 Y")
    independent_variables: list[str] = Field(default_factory=list, description="解析后的自变量 X 列表")
    controls: list[str] = Field(default_factory=list, description="控制变量列表")
    analysis_grain: str = Field(..., description="分析粒度，如：firm-year、bank-year")

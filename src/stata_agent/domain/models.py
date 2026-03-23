from pathlib import Path

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(..., description="自然语言研究题目")
    dependent_variable: str = Field(..., description="因变量 Y，如：ROA、风险承担等")
    independent_variables: list[str] = Field(..., min_length=1, description="自变量 X 列表，至少包含一个")
    entity_scope: str = Field(..., description="样本范围，如：A股上市公司、银行等")
    time_range: str = Field(..., description="时间范围，如：2010-2023")
    empirical_requirements: str = Field(default="构建基准回归模型", description="实证要求")
    output_preferences: list[str] = Field(default_factory=list, description="输出偏好")


class ResearchSpec(BaseModel):
    topic: str = Field(..., description="解析后的研究主题")
    dependent_variable: str = Field(..., description="解析后的因变量 Y")
    independent_variables: list[str] = Field(default_factory=list, description="解析后的自变量 X 列表")
    controls: list[str] = Field(default_factory=list, description="控制变量列表")
    analysis_grain: str = Field(..., description="分析粒度，如：firm-year、bank-year")


class VariableBinding(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    confidence: float


class QueryPlan(BaseModel):
    table_name: str
    columns: list[str] = Field(default_factory=list)
    condition: str | None = None


class ResearchBundle(BaseModel):
    run_id: str
    spec: ResearchSpec | None = None
    dataset_path: Path | None = None
    artifacts: list[Path] = Field(default_factory=list)


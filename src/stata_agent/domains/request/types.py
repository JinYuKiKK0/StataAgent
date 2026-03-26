from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(..., description="自然语言研究题目")
    dependent_variable: str = Field(..., description="因变量 Y，如：ROA、风险承担等")
    independent_variables: list[str] = Field(
        ..., min_length=1, description="自变量 X 列表，至少包含一个"
    )
    entity_scope: str = Field(..., description="样本范围，如：A股上市公司、银行等")
    time_range: str = Field(
        ...,
        pattern=r"^\d{4}-\d{4}$",
        description="时间范围，格式必须为 YYYY-YYYY，如：2010-2023",
    )
    empirical_requirements: str = Field(
        default="构建基准回归模型", description="实证要求"
    )
    output_preferences: list[str] = Field(default_factory=list, description="输出偏好")

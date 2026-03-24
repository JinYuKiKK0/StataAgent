from pydantic import BaseModel, Field


class ResearchSpec(BaseModel):
    topic: str = Field(..., description="解析后的研究主题")
    dependent_variable: str = Field(..., description="解析后的因变量 Y")
    independent_variables: list[str] = Field(default_factory=list, description="解析后的自变量 X 列表")
    entity_scope: str = Field(..., description="解析后的样本范围")
    time_start_year: int = Field(..., description="起始年份")
    time_end_year: int = Field(..., description="结束年份")
    control_variable_candidates: list[str] = Field(default_factory=list, description="控制变量候选列表")
    analysis_grain_candidates: list[str] = Field(
        default_factory=list,
        description="候选分析粒度，如：firm-year、bank-year",
    )


class RequirementParseResult(BaseModel):
    spec: ResearchSpec | None = Field(default=None, description="需求解析成功后得到的研究规范")
    raw_response_text: str | None = Field(default=None, description="模型原始文本输出，用于审计")
    parsing_error: str | None = Field(default=None, description="结构化解析错误")
    failure_reason: str | None = Field(default=None, description="用户可读的失败原因")
    warnings: list[str] = Field(default_factory=list, description="解析过程中的告警")

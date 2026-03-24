from __future__ import annotations

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


class VariableDefinition(BaseModel):
    variable_name: str = Field(..., description="变量名")
    role: str = Field(..., description="变量角色：dependent/independent/control")
    is_locked: bool = Field(..., description="是否为用户锁定的核心变量")
    slot_status: str = Field(..., description="槽位状态：ready/pending_agent_completion")
    frequency_hint: str = Field(..., description="频率提示：annual/quarterly/monthly/unknown")
    source_domain_hint: str = Field(..., description="候选数据域提示")
    note: str | None = Field(default=None, description="补充说明")


class DataRequirementItem(BaseModel):
    variable_name: str = Field(..., description="变量名")
    role: str = Field(..., description="变量角色")
    frequency_hint: str = Field(..., description="频率提示")
    source_domain_hint: str = Field(..., description="候选数据域提示")
    slot_status: str = Field(..., description="槽位状态")


def _empty_data_requirement_items() -> list[DataRequirementItem]:
    return []


class DataRequirementsDraft(BaseModel):
    entity_scope: str = Field(..., description="样本范围")
    time_start_year: int = Field(..., description="起始年份")
    time_end_year: int = Field(..., description="结束年份")
    items: list[DataRequirementItem] = Field(
        default_factory=_empty_data_requirement_items,
        description="数据需求条目",
    )


def _empty_variable_definitions() -> list[VariableDefinition]:
    return []


class VariableRequirementsResult(BaseModel):
    variable_definitions: list[VariableDefinition] = Field(
        default_factory=_empty_variable_definitions,
        description="变量定义表",
    )
    data_requirements_draft: DataRequirementsDraft = Field(..., description="数据需求表草案")
    warnings: list[str] = Field(default_factory=list, description="构建过程告警")

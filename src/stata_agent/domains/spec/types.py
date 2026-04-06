from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchSpec(BaseModel):
    topic: str = Field(..., description="解析后的研究主题")
    dependent_variable: str = Field(..., description="解析后的因变量 Y")
    independent_variables: list[str] = Field(
        default_factory=list, description="解析后的自变量 X 列表"
    )
    entity_scope: str = Field(..., description="解析后的样本范围")
    entity_scope_inferred: bool = Field(
        default=False, description="样本范围是否为 Agent 推断"
    )
    time_start_year: int = Field(..., description="起始年份")
    time_end_year: int = Field(..., description="结束年份")
    analysis_frequency_hint: str = Field(
        default="unknown",
        description="研究级主频率：annual/quarterly/monthly/unknown",
    )
    control_variable_candidates: list[str] = Field(
        default_factory=list, description="控制变量候选列表"
    )
    analysis_grain_candidates: list[str] = Field(
        default_factory=list,
        description="候选分析粒度，如：firm-year、bank-year",
    )


class VariableDefinition(BaseModel):
    variable_name: str = Field(..., description="变量名")
    role: str = Field(..., description="变量角色：dependent/independent/control")
    is_locked: bool = Field(..., description="是否为用户锁定的核心变量")
    slot_status: str = Field(
        ..., description="槽位状态：ready/pending_agent_completion"
    )
    frequency_hint: str = Field(
        ..., description="频率提示：annual/quarterly/monthly/unknown"
    )
    source_domain_hint: str = Field(..., description="候选数据域提示")
    note: str | None = Field(default=None, description="补充说明")

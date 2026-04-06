# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from collections.abc import Mapping
from typing import cast

from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.settings import Settings
from stata_agent.services.spec.contracts import RequirementParseResult
from stata_agent.services.spec.ports import ResearchSpecGenerator
from stata_agent.domains.spec.types import ResearchSpec


class _RequirementSpecPayload(BaseModel):
    topic: str = Field(..., description="归一化后的研究主题")
    dependent_variable: str = Field(..., description="因变量 Y，必须与输入保持一致")
    independent_variables: list[str] = Field(
        default_factory=list, description="自变量 X，必须与输入保持一致"
    )
    entity_scope: str = Field(..., description="样本范围，必须与输入保持一致")
    time_start_year: int = Field(..., description="起始年份")
    time_end_year: int = Field(..., description="结束年份")
    analysis_frequency_hint: str = Field(
        ..., description="研究级主频率：annual/quarterly/monthly/unknown"
    )
    analysis_grain_candidates: list[str] = Field(
        default_factory=list, description="候选分析粒度"
    )
    control_variable_candidates: list[str] = Field(
        default_factory=list, description="控制变量候选列表"
    )
    warnings: list[str] = Field(default_factory=list, description="仅保留真实不确定性")


class TongyiResearchSpecGenerator(ResearchSpecGenerator):
    def __init__(self, settings: Settings) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "\n".join(
                        [
                            "你是 StataAgent 的研究需求解析器。",
                            "你的任务是把用户的研究请求整理成结构化研究规范。",
                            "必须严格保留用户给定的因变量、自变量和时间范围，不能擅自改写。",
                            "如果用户提供了样本范围，必须原样保留；如果用户未提供样本范围，请根据研究题目、因变量和自变量推断合适的样本范围。",
                            "必须推断研究所需的主频率 analysis_frequency_hint，只允许 annual、quarterly、monthly、unknown 四个值。",
                            "只允许补全候选分析粒度与控制变量候选，并在 warnings 中说明真实的不确定点。",
                            "analysis_grain_candidates 至少给出一个候选；control_variable_candidates 中不得包含因变量或自变量本身。",
                        ]
                    ),
                ),
                (
                    "human",
                    "\n".join(
                        [
                            "研究题目: {topic}",
                            "因变量 Y: {dependent_variable}",
                            "自变量 X: {independent_variables}",
                            "样本范围: {entity_scope}",
                            "时间范围: {time_range}",
                            "实证要求: {empirical_requirements}",
                            "请返回结构化结果。",
                        ]
                    ),
                ),
            ]
        )
        model = _build_tongyi_model(settings)
        self._chain = prompt | model.with_structured_output(
            _RequirementSpecPayload, include_raw=True
        )

    def parse_request(self, request: ResearchRequest) -> RequirementParseResult:
        entity_scope_display = (
            request.entity_scope if request.entity_scope else "(未提供，请推断)"
        )
        response = cast(
            Mapping[str, object],
            self._chain.invoke(
                {
                    "topic": request.topic,
                    "dependent_variable": request.dependent_variable,
                    "independent_variables": ", ".join(request.independent_variables),
                    "entity_scope": entity_scope_display,
                    "time_range": request.time_range,
                    "empirical_requirements": request.empirical_requirements,
                }
            ),
        )
        raw_response_text = _stringify_raw_message(response.get("raw"))
        parsing_error = _stringify_error(response.get("parsing_error"))
        parsed = response.get("parsed")
        if not isinstance(parsed, _RequirementSpecPayload):
            return RequirementParseResult(
                raw_response_text=raw_response_text,
                parsing_error=parsing_error,
                failure_reason="Tongyi 未返回可解析的结构化研究规范。",
            )

        spec = ResearchSpec(
            topic=parsed.topic,
            dependent_variable=parsed.dependent_variable,
            independent_variables=parsed.independent_variables,
            entity_scope=parsed.entity_scope,
            entity_scope_inferred=request.entity_scope is None,
            time_start_year=parsed.time_start_year,
            time_end_year=parsed.time_end_year,
            analysis_frequency_hint=parsed.analysis_frequency_hint,
            control_variable_candidates=parsed.control_variable_candidates,
            analysis_grain_candidates=parsed.analysis_grain_candidates,
        )
        return RequirementParseResult(
            spec=spec,
            raw_response_text=raw_response_text,
            parsing_error=parsing_error,
            warnings=parsed.warnings,
        )


def _build_tongyi_model(settings: Settings) -> ChatTongyi:
    return ChatTongyi(
        model=settings.tongyi_model,
        api_key=settings.dashscope_api_key.get_secret_value(),  # pyright: ignore[reportArgumentType]
        streaming=True,
        model_kwargs={"temperature": 0},
    )


def _stringify_raw_message(raw: object) -> str | None:
    if isinstance(raw, BaseMessage):
        content = raw.content
        if isinstance(content, str):
            return content
        return str(content)
    if raw is None:
        return None
    return str(raw)


def _stringify_error(error: object) -> str | None:
    if error is None:
        return None
    return str(error)

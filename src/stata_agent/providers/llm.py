# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

import json
from collections.abc import Mapping
from typing import cast

from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from stata_agent.domains.mapping.ports import VariableSemanticJudgePort
from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import VariableMatchDecision
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult, ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.providers.settings import Settings


class _RequirementSpecPayload(BaseModel):
    topic: str = Field(..., description="归一化后的研究主题")
    dependent_variable: str = Field(..., description="因变量 Y，必须与输入保持一致")
    independent_variables: list[str] = Field(
        default_factory=list, description="自变量 X，必须与输入保持一致"
    )
    entity_scope: str = Field(..., description="样本范围，必须与输入保持一致")
    time_start_year: int = Field(..., description="起始年份")
    time_end_year: int = Field(..., description="结束年份")
    analysis_grain_candidates: list[str] = Field(
        default_factory=list, description="候选分析粒度"
    )
    control_variable_candidates: list[str] = Field(
        default_factory=list, description="控制变量候选列表"
    )
    warnings: list[str] = Field(default_factory=list, description="仅保留真实不确定性")


class _VariableMatchPayload(BaseModel):
    matched: bool = Field(..., description="是否存在语义可接受的候选")
    selected_index: int = Field(
        default=-1, description="命中的候选序号；若无匹配则为 -1"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="匹配置信度")
    rationale: str = Field(..., description="选择或拒绝的主要理由")
    resolved_domain: str = Field(default="", description="解析后的数据域")


class TongyiResearchSpecGenerator:
    def __init__(self, settings: Settings) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "\n".join(
                        [
                            "你是 StataAgent 的研究需求解析器。",
                            "你的任务是把用户的研究请求整理成结构化研究规范。",
                            "必须严格保留用户给定的因变量、自变量、样本范围和时间范围，不能擅自改写。",
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
        response = cast(
            Mapping[str, object],
            self._chain.invoke(
                {
                    "topic": request.topic,
                    "dependent_variable": request.dependent_variable,
                    "independent_variables": ", ".join(request.independent_variables),
                    "entity_scope": request.entity_scope,
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
            time_start_year=parsed.time_start_year,
            time_end_year=parsed.time_end_year,
            control_variable_candidates=parsed.control_variable_candidates,
            analysis_grain_candidates=parsed.analysis_grain_candidates,
        )
        return RequirementParseResult(
            spec=spec,
            raw_response_text=raw_response_text,
            parsing_error=parsing_error,
            warnings=parsed.warnings,
        )


class TongyiVariableSemanticJudge(VariableSemanticJudgePort):
    def __init__(self, settings: Settings) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "\n".join(
                        [
                            "你是 StataAgent 的变量候选判别器。",
                            "你的职责是在给定的 CSMAR 候选中选择语义最匹配的一项，或者明确拒绝所有候选。",
                            "你只能从候选列表中选择，不能发明新的字段或表。",
                            "若候选与变量语义不等价、证据不足或存在明显歧义，必须返回 matched=false。",
                            "resolved_domain 只允许使用候选中的数据库名称或你能直接从候选归纳出的简洁域名。",
                        ]
                    ),
                ),
                (
                    "human",
                    "\n".join(
                        [
                            "研究题目: {topic}",
                            "样本范围: {entity_scope}",
                            "变量: {variable_name}",
                            "变量角色: {role}",
                            "频率提示: {frequency_hint}",
                            "候选列表(JSON): {candidates_json}",
                            "请返回结构化判别结果。",
                        ]
                    ),
                ),
            ]
        )
        model = _build_tongyi_model(settings)
        self._chain = prompt | model.with_structured_output(
            _VariableMatchPayload, include_raw=True
        )

    def judge(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        definition: VariableDefinition,
        candidates: list[CsmarFieldCandidate],
    ) -> VariableMatchDecision:
        if not candidates:
            return VariableMatchDecision(
                matched=False,
                rationale="无候选可供语义判别。",
            )

        response = cast(
            Mapping[str, object],
            self._chain.invoke(
                {
                    "topic": spec.topic,
                    "entity_scope": spec.entity_scope,
                    "variable_name": definition.variable_name,
                    "role": definition.role,
                    "frequency_hint": definition.frequency_hint,
                    "candidates_json": _format_candidates(candidates),
                }
            ),
        )
        parsed = response.get("parsed")
        if not isinstance(parsed, _VariableMatchPayload):
            raise RuntimeError("Tongyi 未返回可解析的变量候选判别结果。")

        if (
            not parsed.matched
            or parsed.selected_index < 0
            or parsed.selected_index >= len(candidates)
        ):
            return VariableMatchDecision(
                matched=False,
                confidence=parsed.confidence,
                rationale=parsed.rationale,
                resolved_domain=parsed.resolved_domain,
            )

        selected = candidates[parsed.selected_index]
        return VariableMatchDecision(
            matched=True,
            selected_table_name=selected.table_name,
            selected_field_name=selected.field_name,
            confidence=parsed.confidence,
            rationale=parsed.rationale,
            resolved_domain=parsed.resolved_domain or selected.csmar_database,
        )


def _build_tongyi_model(settings: Settings) -> ChatTongyi:
    return ChatTongyi(
        model=settings.tongyi_model,
        api_key=settings.dashscope_api_key,
        streaming=True,
        model_kwargs={"temperature": 0},
    )


def _format_candidates(candidates: list[CsmarFieldCandidate]) -> str:
    payload = []
    for index, candidate in enumerate(candidates):
        payload.append(
            {
                "index": index,
                "database": candidate.csmar_database,
                "table_name": candidate.table_name,
                "table_label": candidate.table_label,
                "field_name": candidate.field_name,
                "field_label": candidate.field_label,
                "field_description": candidate.field_description,
                "aliases": candidate.aliases,
                "frequency_tags": candidate.frequency_tags,
                "match_evidence": candidate.match_evidence,
            }
        )
    return json.dumps(payload, ensure_ascii=False)


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

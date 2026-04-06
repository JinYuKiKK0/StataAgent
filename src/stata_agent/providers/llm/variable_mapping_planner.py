# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import json
from collections.abc import Mapping
from typing import cast

from langchain.agents import create_agent
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.providers.llm.variable_mapping_toolkit import VariableMappingToolkit
from stata_agent.providers.settings import Settings
from stata_agent.services.mapping.contracts import VariableMappingPlanItem
from stata_agent.services.mapping.contracts import VariableMappingPlanResult
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.mapping.ports import MappingPlannerPort


class _VariableMappingPayloadItem(BaseModel):
    variable_name: str
    matched: bool = Field(..., description="是否已确认到具体字段")
    database_name: str = Field(default="", description="数据库名称")
    table_code: str = Field(default="", description="表代码")
    table_name: str = Field(default="", description="表名称")
    field_name: str = Field(default="", description="字段代码")
    field_label: str = Field(default="", description="字段标签")
    frequency_match: bool = Field(default=False, description="字段频率是否匹配研究频率")
    evidence: str = Field(default="", description="schema 级证据摘要")
    rationale: str = Field(default="", description="选择或拒绝的理由")
    trace_id: str = Field(default="", description="确认字段存在的 schema trace_id")


class _VariableMappingPayload(BaseModel):
    items: list[_VariableMappingPayloadItem] = Field(
        default_factory=list,
        description="必须为每个输入变量输出一条记录。",
    )
    warnings: list[str] = Field(default_factory=list, description="真实的不确定性说明")


class TongyiVariableMappingPlanner(MappingPlannerPort):
    def __init__(self, settings: Settings) -> None:
        self._model = ChatTongyi(
            model=settings.tongyi_model,
            api_key=settings.dashscope_api_key.get_secret_value(),  # pyright: ignore[reportArgumentType]
            streaming=True,
            model_kwargs={"temperature": 0},
        )

    def plan(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        metadata_provider: CsmarMetadataProviderPort,
    ) -> VariableMappingPlanResult:
        toolkit = VariableMappingToolkit(metadata_provider)
        agent = create_agent(
            model=self._model,
            tools=toolkit.build_tools(),
            system_prompt=_build_system_prompt(),
        )
        result = cast(
            Mapping[str, object],
            agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": _build_mapping_request(
                                request=request,
                                spec=spec,
                                variable_definitions=variable_definitions,
                            ),
                        }
                    ]
                }
            ),
        )
        messages = cast(list[BaseMessage], result.get("messages", []))
        payload = self._extract_structured_output(messages)
        if not isinstance(payload, _VariableMappingPayload):
            raise RuntimeError("变量映射 agent 未返回可解析的结构化结果。")
        return VariableMappingPlanResult(
            items=[
                VariableMappingPlanItem(
                    variable_name=item.variable_name,
                    matched=item.matched,
                    database_name=item.database_name,
                    table_code=item.table_code,
                    table_name=item.table_name,
                    field_name=item.field_name,
                    field_label=item.field_label,
                    frequency_match=item.frequency_match,
                    evidence=item.evidence,
                    rationale=item.rationale,
                    trace_id=item.trace_id,
                )
                for item in payload.items
            ],
            warnings=payload.warnings,
        )

    def _extract_structured_output(
        self, messages: list[BaseMessage]
    ) -> _VariableMappingPayload | None:
        structured_model = self._model.with_structured_output(_VariableMappingPayload)
        extraction_prompt = (
            "基于以上对话历史，请提取变量映射结果。"
            "必须为每个输入变量输出一条记录，包含 variable_name、matched、"
            "database_name、table_code、table_name、field_name、field_label、"
            "frequency_match、evidence、rationale、trace_id 字段。"
        )
        all_messages = list(messages) + [
            {"role": "user", "content": extraction_prompt}
        ]
        result = structured_model.invoke(all_messages)
        if isinstance(result, _VariableMappingPayload):
            return result
        return None


def _build_system_prompt() -> str:
    return "\n".join(
        [
            "你是 StataAgent 的 Phase1 变量映射代理。",
            "你的唯一职责是把变量定义映射到可用于 probe 的 CSMAR 字段。",
            "你只能使用 csmar_list_databases、csmar_list_tables、csmar_get_table_schema。",
            "严禁使用 search_tables、search_fields 或任何下载/解压相关能力。",
            "必须遵循 list_databases -> list_tables -> get_table_schema 的逐级路径。",
            "只有读取过 schema 的字段才能被标记为 matched=true。",
            "每个 matched=true 的结果都必须带上用于确认字段的 trace_id。",
            "如果工具返回 ok=false 且 code=budget_exhausted，立即停止继续调用工具，并基于当前证据输出结果。",
            "如果变量在当前预算内无法高置信映射，返回 matched=false，并在 rationale 中说明原因。",
            "不要重复读取同一数据库或同一表的 schema。",
            "最终必须对每个输入变量输出一条结果记录。",
        ]
    )


def _build_mapping_request(
    *,
    request: ResearchRequest,
    spec: ResearchSpec,
    variable_definitions: list[VariableDefinition],
) -> str:
    return "\n".join(
        [
            f"研究题目: {request.topic}",
            f"样本范围: {spec.entity_scope}",
            f"时间范围: {spec.time_start_year}-{spec.time_end_year}",
            f"主频率: {spec.analysis_frequency_hint}",
            f"候选分析粒度: {', '.join(spec.analysis_grain_candidates)}",
            "变量定义(JSON): "
            + json.dumps(
                [item.model_dump(mode="json") for item in variable_definitions],
                ensure_ascii=False,
            ),
            "请返回结构化映射结果。",
        ]
    )

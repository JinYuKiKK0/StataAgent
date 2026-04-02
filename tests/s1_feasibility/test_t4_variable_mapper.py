"""S1-T4 CSMAR 探针级变量映射测试。"""

import pytest

from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest
from stata_agent.domains.mapping.types import VariableMatchDecision
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.services.requirement_parser import RequirementParser
from stata_agent.services.variable_mapper import VariableMapper
from stata_agent.services.variable_requirements_builder import VariableRequirementsBuilder

pytest_plugins = ["tests.live_api_support"]


class _FakeMetadataProvider:
    def __init__(self, matches: dict[str, list[CsmarFieldCandidate]]) -> None:
        self._matches = matches

    def search_field_candidates(
        self, request: CsmarFieldSearchRequest
    ) -> list[CsmarFieldCandidate]:
        return list(self._matches.get(request.variable_name, []))

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        raise AssertionError("变量映射测试不应调用 probe。")


class _FakeSemanticJudge:
    def __init__(self, decisions: dict[str, VariableMatchDecision]) -> None:
        self._decisions = decisions

    def judge(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        definition: VariableDefinition,
        candidates: list[CsmarFieldCandidate],
    ) -> VariableMatchDecision:
        return self._decisions[definition.variable_name]


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="企业资产规模与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资产总计"],
        entity_scope="A股上市公司",
        time_range="2018-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="企业资产规模与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资产总计"],
        entity_scope="A股上市公司",
        time_start_year=2018,
        time_end_year=2023,
        control_variable_candidates=["资产负债率"],
        analysis_grain_candidates=["firm-year"],
    )


def _build_definitions() -> list[VariableDefinition]:
    builder = VariableRequirementsBuilder()
    return builder.build(_build_spec()).variable_definitions


def test_mapper_uses_semantic_judge_for_synonymous_field_names() -> None:
    """验证字面不同但语义等价的变量名会通过语义判别映射到同一字段。"""
    provider = _FakeMetadataProvider(
        {
            "ROA": [
                CsmarFieldCandidate(
                    variable_name="ROA",
                    table_name="FS_Comins",
                    field_name="ROA",
                    csmar_database="财务报表",
                    field_label="资产回报率",
                    aliases=["ROA", "资产回报率"],
                    match_evidence=["alias精确命中=ROA"],
                    frequency_tags=["annual", "quarterly"],
                )
            ],
            "资产总计": [
                CsmarFieldCandidate(
                    variable_name="资产总计",
                    table_name="FS_Combas",
                    field_name="ASSET",
                    csmar_database="财务报表",
                    field_label="总资产",
                    aliases=["总资产", "资产规模"],
                    match_evidence=["alias语义接近=总资产"],
                    frequency_tags=["annual", "quarterly"],
                )
            ]
        }
    )
    judge = _FakeSemanticJudge(
        {
            "ROA": VariableMatchDecision(
                matched=True,
                selected_table_name="FS_Comins",
                selected_field_name="ROA",
                confidence=0.95,
                rationale="ROA 与候选字段完全一致。",
                resolved_domain="财务报表",
            ),
            "资产总计": VariableMatchDecision(
                matched=True,
                selected_table_name="FS_Combas",
                selected_field_name="ASSET",
                confidence=0.92,
                rationale="资产总计与总资产语义等价。",
                resolved_domain="财务报表",
            ),
        }
    )
    mapper = VariableMapper(metadata_provider=provider, semantic_judge=judge)

    result = mapper.map_probe_bindings(
        request=_build_request(),
        spec=_build_spec(),
        variable_definitions=_build_definitions(),
    )

    assert result.failure_reason is None
    binding = next(item for item in result.bindings if item.variable_name == "资产总计")
    assert binding.field_name == "ASSET"
    assert binding.source == "csmar_semantic_judge"
    resolved = next(
        item
        for item in result.resolved_variable_definitions
        if item.variable_name == "资产总计"
    )
    assert resolved.source_domain_hint == "财务报表"


def test_mapper_fails_fast_when_hard_variable_has_no_semantic_match() -> None:
    """验证 Hard Contract 即使拿到候选，也会在语义判别拒绝时立即失败。"""
    provider = _FakeMetadataProvider(
        {
            "ROA": [
                CsmarFieldCandidate(
                    variable_name="ROA",
                    table_name="FS_Comins",
                    field_name="ROA",
                    csmar_database="财务报表",
                    field_label="资产回报率",
                    aliases=["ROA", "资产回报率"],
                    match_evidence=["alias精确命中=ROA"],
                    frequency_tags=["annual"],
                )
            ],
            "资产总计": [
                CsmarFieldCandidate(
                    variable_name="资产总计",
                    table_name="FS_Combas",
                    field_name="LIABILITY",
                    csmar_database="财务报表",
                    field_label="总负债",
                    aliases=["总负债"],
                    match_evidence=["字段标签包含变量名"],
                    frequency_tags=["annual"],
                )
            ]
        }
    )
    judge = _FakeSemanticJudge(
        {
            "ROA": VariableMatchDecision(
                matched=True,
                selected_table_name="FS_Comins",
                selected_field_name="ROA",
                confidence=0.95,
                rationale="ROA 与候选字段完全一致。",
                resolved_domain="财务报表",
            ),
            "资产总计": VariableMatchDecision(
                matched=False,
                confidence=0.15,
                rationale="候选字段语义不等价。",
            ),
        }
    )
    mapper = VariableMapper(metadata_provider=provider, semantic_judge=judge)

    result = mapper.map_probe_bindings(
        request=_build_request(),
        spec=_build_spec(),
        variable_definitions=_build_definitions(),
    )

    assert result.failure_reason is not None
    assert "资产总计" in result.failure_reason
    assert result.bindings == []


def test_mapper_keeps_soft_gap_summary_without_abort() -> None:
    """验证 Soft Contract 缺口只进入摘要，不会导致整个映射阶段失败。"""
    provider = _FakeMetadataProvider(
        {
            "ROA": [
                CsmarFieldCandidate(
                    variable_name="ROA",
                    table_name="FS_Comins",
                    field_name="ROA",
                    csmar_database="财务报表",
                    field_label="资产回报率",
                    aliases=["ROA", "资产回报率"],
                    match_evidence=["alias精确命中=ROA"],
                    frequency_tags=["annual"],
                )
            ],
            "资产总计": [
                CsmarFieldCandidate(
                    variable_name="资产总计",
                    table_name="FS_Combas",
                    field_name="ASSET",
                    csmar_database="财务报表",
                    field_label="总资产",
                    aliases=["总资产", "资产规模"],
                    match_evidence=["alias语义接近=总资产"],
                    frequency_tags=["annual"],
                )
            ],
        }
    )
    mapper = VariableMapper(metadata_provider=provider)
    definitions = _build_definitions() + [
        VariableDefinition(
            variable_name="不存在的控制变量",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
            source_domain_hint="pending_resolution",
        )
    ]

    result = mapper.map_probe_bindings(
        request=_build_request(),
        spec=_build_spec(),
        variable_definitions=definitions,
    )

    assert result.failure_reason is None
    assert "不存在的控制变量" in result.soft_contract_gaps


@pytest.mark.live_api
def test_mapper_generates_bindings_from_real_csmar_metadata(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证映射节点会调用真实 CSMAR 元数据并生成非空绑定。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None
    builder = VariableRequirementsBuilder()
    build_result = builder.build(parse_result.spec)

    mapper = VariableMapper(metadata_provider=live_csmar_provider)
    result = mapper.map_probe_bindings(
        request=live_request,
        spec=parse_result.spec,
        variable_definitions=build_result.variable_definitions,
    )

    assert result.failure_reason is None
    assert result.bindings
    assert parse_result.spec.dependent_variable in result.hard_contract_variables


@pytest.mark.live_api
def test_mapper_fails_fast_when_real_hard_variable_has_no_mapping(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    failing_live_request: ResearchRequest,
) -> None:
    """验证真实映射流程中 Hard Contract 不可映射时会立刻失败。"""
    parse_result = live_parser.parse(failing_live_request)
    assert parse_result.spec is not None
    builder = VariableRequirementsBuilder()
    build_result = builder.build(parse_result.spec)

    mapper = VariableMapper(metadata_provider=live_csmar_provider)
    result = mapper.map_probe_bindings(
        request=failing_live_request,
        spec=parse_result.spec,
        variable_definitions=build_result.variable_definitions,
    )

    assert result.failure_reason is not None
    assert result.bindings == []

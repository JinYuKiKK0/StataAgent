"""S1-T4 变量映射 live smoke 测试。"""

import pytest

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.providers.llm_mapping import TongyiVariableMappingPlanner
from stata_agent.providers.settings import Settings
from stata_agent.services.requirement_parser import RequirementParser
from stata_agent.services.variable_mapper import VariableMapper
from stata_agent.services.variable_requirements_builder import VariableRequirementsBuilder

pytest_plugins = ["tests.live_api_support"]


@pytest.mark.live_api
def test_mapper_generates_bindings_from_real_csmar_metadata(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_settings: Settings,
    live_request: ResearchRequest,
) -> None:
    """验证映射节点会调用真实 CSMAR 元数据并生成非空绑定。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None
    builder = VariableRequirementsBuilder()
    build_result = builder.build(parse_result.spec)

    mapper = VariableMapper(
        metadata_provider=live_csmar_provider,
        planner=TongyiVariableMappingPlanner(live_settings),
    )
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
    live_settings: Settings,
    failing_live_request: ResearchRequest,
) -> None:
    """验证真实映射流程中 Hard Contract 不可映射时会立刻失败。"""
    parse_result = live_parser.parse(failing_live_request)
    assert parse_result.spec is not None
    builder = VariableRequirementsBuilder()
    build_result = builder.build(parse_result.spec)

    mapper = VariableMapper(
        metadata_provider=live_csmar_provider,
        planner=TongyiVariableMappingPlanner(live_settings),
    )
    result = mapper.map_probe_bindings(
        request=failing_live_request,
        spec=parse_result.spec,
        variable_definitions=build_result.variable_definitions,
    )

    assert result.failure_reason is not None
    assert result.bindings == []

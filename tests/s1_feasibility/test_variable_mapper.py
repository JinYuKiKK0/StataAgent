"""S1-T4 CSMAR 探针级变量映射真实接口集成测试。"""

import pytest

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.services.requirement_parser import RequirementParser
from stata_agent.services.variable_mapper import VariableMapper
from stata_agent.services.variable_requirements_builder import VariableRequirementsBuilder

pytest_plugins = ["tests.live_api_support"]

pytestmark = pytest.mark.live_api


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


def test_mapper_keeps_soft_gap_summary_without_abort(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证真实映射流程中 Soft Contract 缺口只会进入摘要，不会中止流程。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None
    builder = VariableRequirementsBuilder()
    build_result = builder.build(parse_result.spec)

    definitions = list(build_result.variable_definitions)
    definitions.append(
        VariableDefinition(
            variable_name="不存在的控制变量",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
            source_domain_hint="finance_statement",
        )
    )

    mapper = VariableMapper(metadata_provider=live_csmar_provider)
    result = mapper.map_probe_bindings(
        request=live_request,
        spec=parse_result.spec,
        variable_definitions=definitions,
    )

    assert result.failure_reason is None
    assert "不存在的控制变量" in result.soft_contract_gaps

"""S1-T4 变量映射 live smoke 测试。"""

import pytest

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.providers.csmar.node_scoped_client import NodeScopedCsmarProviderFactory
from stata_agent.providers.llm import TongyiVariableMappingPlanner
from stata_agent.providers.settings import Settings
from stata_agent.services.mapping.materialize_bindings import VariableBindingMaterializer
from stata_agent.services.mapping.plan_mapping import ProbeMappingPlanner
from stata_agent.services.spec.requirement_parser import RequirementParser
from stata_agent.services.spec.variable_requirements import VariableRequirementsBuilder

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

    planner = ProbeMappingPlanner(
        metadata_provider=live_csmar_provider,
        planner=TongyiVariableMappingPlanner(live_settings),
        scope_factory=NodeScopedCsmarProviderFactory(),
    )
    plan_result = planner.plan_probe_mapping(
        request=live_request,
        spec=parse_result.spec,
        variable_definitions=build_result.variable_definitions,
    )
    result = VariableBindingMaterializer().materialize_variable_bindings(
        request=live_request,
        spec=parse_result.spec,
        variable_definitions=build_result.variable_definitions,
        planning_result=plan_result,
    )

    assert result.failure_reason is None
    assert result.bindings
    assert parse_result.spec.dependent_variable in result.hard_contract_variables




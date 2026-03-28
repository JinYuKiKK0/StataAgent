"""架构契约测试：`ResearchState` 只能依赖领域层边界对象。"""

def test_research_state_uses_domain_contracts() -> None:
    """验证工作流状态对象的字段类型仍然绑定到受控领域契约，而非裸结构。"""
    from stata_agent.domains.fetch.types import DataContractBundle
    from stata_agent.domains.fetch.types import ProbeCoverageResult
    from stata_agent.domains.mapping.types import VariableBinding
    from stata_agent.domains.mapping.types import VariableMappingResult
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.domains.spec.types import DataRequirementsDraft
    from stata_agent.domains.spec.types import RequirementParseResult
    from stata_agent.domains.spec.types import ResearchSpec
    from stata_agent.domains.spec.types import VariableDefinition
    from stata_agent.workflow.state import ResearchState

    assert ResearchState.model_fields["request"].annotation is ResearchRequest
    assert ResearchState.model_fields["spec"].annotation == ResearchSpec | None
    assert (
        ResearchState.model_fields["parse_result"].annotation
        == RequirementParseResult | None
    )
    assert (
        ResearchState.model_fields["variable_definitions"].annotation
        == list[VariableDefinition] | None
    )
    assert (
        ResearchState.model_fields["data_requirements_draft"].annotation
        == DataRequirementsDraft | None
    )
    assert (
        ResearchState.model_fields["variable_bindings"].annotation
        == list[VariableBinding] | None
    )
    assert (
        ResearchState.model_fields["variable_mapping_result"].annotation
        == VariableMappingResult | None
    )
    assert (
        ResearchState.model_fields["probe_coverage_result"].annotation
        == ProbeCoverageResult | None
    )
    assert (
        ResearchState.model_fields["data_contract_bundle"].annotation
        == DataContractBundle | None
    )

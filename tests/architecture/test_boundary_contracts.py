def test_research_state_uses_domain_contracts() -> None:
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
    assert ResearchState.model_fields["parse_result"].annotation == RequirementParseResult | None
    assert ResearchState.model_fields["variable_definitions"].annotation == list[VariableDefinition] | None
    assert ResearchState.model_fields["data_requirements_draft"].annotation == DataRequirementsDraft | None
    assert ResearchState.model_fields["variable_bindings"].annotation == list[VariableBinding] | None
    assert ResearchState.model_fields["variable_mapping_result"].annotation == VariableMappingResult | None

def test_research_state_uses_domain_contracts() -> None:
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.domains.spec.types import RequirementParseResult, ResearchSpec
    from stata_agent.workflow.state import ResearchState

    assert ResearchState.model_fields["request"].annotation is ResearchRequest
    assert ResearchState.model_fields["spec"].annotation == ResearchSpec | None
    assert ResearchState.model_fields["parse_result"].annotation == RequirementParseResult | None

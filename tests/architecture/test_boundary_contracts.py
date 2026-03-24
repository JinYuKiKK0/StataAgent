def test_research_state_uses_domain_contracts() -> None:
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.domains.spec.types import ResearchSpec
    from stata_agent.workflow.state import ResearchState

    assert ResearchState.model_fields["request"].annotation is ResearchRequest
    assert ResearchState.model_fields["spec"].annotation == ResearchSpec | None


def test_domain_models_reexport_split_contracts() -> None:
    from stata_agent.domain.models import QueryPlan, ResearchBundle, ResearchRequest, ResearchSpec, VariableBinding
    from stata_agent.domains.fetch.types import QueryPlan as SplitQueryPlan
    from stata_agent.domains.judgement.types import ResearchBundle as SplitResearchBundle
    from stata_agent.domains.mapping.types import VariableBinding as SplitVariableBinding
    from stata_agent.domains.request.types import ResearchRequest as SplitResearchRequest
    from stata_agent.domains.spec.types import ResearchSpec as SplitResearchSpec

    assert ResearchRequest is SplitResearchRequest
    assert ResearchSpec is SplitResearchSpec
    assert VariableBinding is SplitVariableBinding
    assert QueryPlan is SplitQueryPlan
    assert ResearchBundle is SplitResearchBundle

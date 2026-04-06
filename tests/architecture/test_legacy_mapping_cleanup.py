"""架构契约测试：领域层不再暴露 provider 过程 DTO，旧映射链路保持清退。"""


def test_domain_layer_no_longer_exports_provider_side_mapping_payloads() -> None:
    """验证 trace、预算和工具返回体已下沉到 provider/contracts 层。"""
    import stata_agent.domains.mapping as mapping_domain
    import stata_agent.domains.spec as spec_domain
    import stata_agent.providers.llm as llm_provider
    from stata_agent.providers.csmar.client import CsmarBridgeClient

    assert hasattr(llm_provider, "TongyiResearchSpecGenerator")
    assert hasattr(mapping_domain, "VariableBinding")
    assert hasattr(spec_domain, "ResearchSpec")

    assert not hasattr(llm_provider, "TongyiVariableSemanticJudge")
    assert not hasattr(mapping_domain, "VariableSemanticJudgePort")
    assert not hasattr(mapping_domain, "VariableMatchDecision")
    assert not hasattr(mapping_domain, "CsmarFieldCandidate")
    assert not hasattr(mapping_domain, "CsmarToolTrace")
    assert not hasattr(mapping_domain, "VariableMappingResult")
    assert not hasattr(spec_domain, "RequirementParseResult")
    assert not hasattr(spec_domain, "DataRequirementsDraft")
    assert not hasattr(CsmarBridgeClient, "search_tables")
    assert not hasattr(CsmarBridgeClient, "search_fields")

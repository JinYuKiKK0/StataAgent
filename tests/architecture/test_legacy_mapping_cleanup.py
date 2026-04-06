"""架构契约测试：应用层不再暴露旧变量映射链路。"""


def test_app_layer_no_longer_exports_legacy_mapping_symbols() -> None:
    """验证旧 semantic judge 与 search shortcut 已从应用层退场。"""
    import stata_agent.domains.mapping as mapping_domain
    import stata_agent.providers.llm as llm_provider
    from stata_agent.providers.csmar.client import CsmarBridgeClient

    assert hasattr(llm_provider, "TongyiResearchSpecGenerator")
    assert not hasattr(llm_provider, "TongyiVariableSemanticJudge")
    assert not hasattr(mapping_domain, "VariableSemanticJudgePort")
    assert not hasattr(mapping_domain, "VariableMatchDecision")
    assert not hasattr(mapping_domain, "CsmarFieldCandidate")
    assert not hasattr(CsmarBridgeClient, "search_tables")
    assert not hasattr(CsmarBridgeClient, "search_fields")

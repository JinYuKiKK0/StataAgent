def test_new_layout_modules_import() -> None:
    from stata_agent.interfaces.cli import app
    from stata_agent.providers.settings import get_settings
    from stata_agent.workflow.orchestrator import ApplicationOrchestrator
    from stata_agent.workflow.state import ResearchState

    assert app is not None
    assert get_settings is not None
    assert ApplicationOrchestrator is not None
    assert ResearchState is not None

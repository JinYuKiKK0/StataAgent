"""布局测试：稳定入口模块仍可被导入，说明基础目录结构没有漂移。"""

def test_new_layout_modules_import() -> None:
    """验证 CLI、配置、编排器和状态入口仍处于预期位置并可正常导入。"""
    from stata_agent.interfaces.cli import app
    from stata_agent.providers.settings import get_settings
    from stata_agent.workflow.orchestrator import ApplicationOrchestrator
    from stata_agent.workflow.state import ResearchState

    assert app is not None
    assert get_settings is not None
    assert ApplicationOrchestrator is not None
    assert ResearchState is not None

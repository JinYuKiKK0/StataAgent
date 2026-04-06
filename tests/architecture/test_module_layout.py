"""布局测试：重构后的正式入口与能力域模块仍位于受控位置。"""


def test_new_layout_modules_import() -> None:
    """验证 CLI、配置、编排入口与新能力域子包都处于预期位置。"""
    from stata_agent.interfaces.cli import app
    from stata_agent.providers.csmar.types import CsmarToolTrace
    from stata_agent.providers.llm.research_spec_generator import (
        TongyiResearchSpecGenerator,
    )
    from stata_agent.providers.llm.variable_mapping_planner import (
        TongyiVariableMappingPlanner,
    )
    from stata_agent.providers.settings import get_settings
    from stata_agent.services.contract.data_contract_builder import DataContractBuilder
    from stata_agent.services.mapping.materialize_bindings import (
        VariableBindingMaterializer,
    )
    from stata_agent.services.mapping.plan_mapping import ProbeMappingPlanner
    from stata_agent.services.probe.executor import ProbeExecutor
    from stata_agent.services.probe.summarizer import ProbeCoverageSummarizer
    from stata_agent.services.spec.requirement_parser import RequirementParser
    from stata_agent.services.spec.variable_requirements import (
        VariableRequirementsBuilder,
    )
    from stata_agent.workflow.bootstrap import build_application_dependencies
    from stata_agent.workflow.orchestrator import ApplicationOrchestrator
    from stata_agent.workflow.state import ResearchState

    assert app is not None
    assert get_settings is not None
    assert build_application_dependencies is not None
    assert ApplicationOrchestrator is not None
    assert ResearchState is not None
    assert RequirementParser is not None
    assert VariableRequirementsBuilder is not None
    assert ProbeMappingPlanner is not None
    assert VariableBindingMaterializer is not None
    assert ProbeExecutor is not None
    assert ProbeCoverageSummarizer is not None
    assert DataContractBuilder is not None
    assert TongyiResearchSpecGenerator is not None
    assert TongyiVariableMappingPlanner is not None
    assert CsmarToolTrace is not None


def test_legacy_workflow_port_layer_and_placeholder_modules_are_removed() -> None:
    """验证重复端口仓库与无行为占位模块不再留在活跃代码路径中。"""
    import importlib.util

    assert importlib.util.find_spec("stata_agent.workflow.ports") is None
    assert importlib.util.find_spec("stata_agent.services.model_planner") is None
    assert importlib.util.find_spec("stata_agent.services.panel_builder") is None
    assert importlib.util.find_spec("stata_agent.services.quality_gate") is None
    assert importlib.util.find_spec("stata_agent.services.result_judge") is None
    assert importlib.util.find_spec("stata_agent.workflow.stages.phase2_modeling") is None
    assert (
        importlib.util.find_spec("stata_agent.workflow.stages.phase3_execution") is None
    )

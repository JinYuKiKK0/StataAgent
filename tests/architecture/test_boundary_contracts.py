"""架构契约测试：`ResearchState` 只暴露分组后的阶段产物与编排审计对象。"""


def test_research_state_groups_phase1_and_workflow_artifacts() -> None:
    """验证工作流状态对象不再平铺 S1 过程字段，而是收口到阶段与审计切片。"""
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.workflow.gateway import GatewayState
    from stata_agent.workflow.state import Phase1Artifacts
    from stata_agent.workflow.state import ResearchState
    from stata_agent.workflow.state import WorkflowAuditState

    assert ResearchState.model_fields["request"].annotation is ResearchRequest
    assert ResearchState.model_fields["phase1_artifacts"].annotation is Phase1Artifacts
    assert ResearchState.model_fields["workflow_audit"].annotation is WorkflowAuditState
    assert ResearchState.model_fields["gateway_state"].annotation is GatewayState


def test_phase1_artifacts_only_depend_on_domain_and_service_contracts() -> None:
    """验证 S1 active state 只保留当前工作集与终态契约，不再常驻调试型中间结果。"""
    from stata_agent.domains.contract.types import DataContractBundle
    from stata_agent.domains.mapping.types import VariableBinding
    from stata_agent.domains.spec.types import ResearchSpec
    from stata_agent.domains.spec.types import VariableDefinition
    from stata_agent.services.probe.contracts import ProbeCoverageResult
    from stata_agent.services.spec.contracts import DataRequirementsDraft
    from stata_agent.workflow.state import Phase1Artifacts
    from stata_agent.workflow.state import ResearchState

    assert Phase1Artifacts.model_fields["spec"].annotation == ResearchSpec | None
    assert (
        Phase1Artifacts.model_fields["variable_definitions"].annotation
        == list[VariableDefinition] | None
    )
    assert (
        Phase1Artifacts.model_fields["data_requirements_draft"].annotation
        == DataRequirementsDraft | None
    )
    assert (
        Phase1Artifacts.model_fields["variable_bindings"].annotation
        == list[VariableBinding] | None
    )
    assert (
        Phase1Artifacts.model_fields["probe_coverage_result"].annotation
        == ProbeCoverageResult | None
    )
    assert (
        Phase1Artifacts.model_fields["data_contract_bundle"].annotation
        == DataContractBundle | None
    )
    assert "parse_result" not in Phase1Artifacts.model_fields
    assert "mapping_plan_result" not in Phase1Artifacts.model_fields
    assert "mapping_result" not in Phase1Artifacts.model_fields
    assert "probe_results_raw" not in Phase1Artifacts.model_fields
    assert ResearchState.model_fields["phase1_artifacts"].annotation is Phase1Artifacts

"""应用层工作流编排与 Gateway 恢复测试。

该文件覆盖 `ApplicationOrchestrator`，它把 Phase 1 可行性流水线接到
S1-T7 的 Gateway 审批节点上，是当前单次实证工作流最外层的协调者。
它的角色不是重新实现各个业务节点，而是负责持久化线程、命中审批中断、
处理 approve/reject 恢复路径，并把失败原因稳定地折叠回 `ResearchState`。
"""

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.domains.spec.types import RequirementParseResult, ResearchSpec
from stata_agent.domains.fetch.types import GatewayDecision, ProbeCoverageResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.providers.settings import Settings
from stata_agent.providers.settings import SettingsError
from stata_agent.workflow.orchestrator import ApplicationOrchestrator
from stata_agent.workflow.orchestrator import WorkflowBootstrapError
from stata_agent.workflow.types import RunStage


class SuccessfulParser:
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(
            spec=ResearchSpec(
                topic=request.topic,
                dependent_variable=request.dependent_variable,
                independent_variables=request.independent_variables,
                entity_scope=request.entity_scope,
                time_start_year=2010,
                time_end_year=2023,
                control_variable_candidates=["资产规模"],
                analysis_grain_candidates=["bank-year"],
            ),
            raw_response_text="ok",
        )


class FailingParser:
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(
            raw_response_text="bad output",
            failure_reason="需求解析失败：Tongyi 未产出可用的研究规范。",
        )


class SuccessfulMapper:
    def map_probe_bindings(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingResult:
        return VariableMappingResult(
            bindings=[
                VariableBinding(
                    variable_name=spec.dependent_variable,
                    table_name="FS_Comins",
                    field_name="ROA",
                    confidence=0.9,
                    csmar_database="财务报表",
                    contract_tier="hard",
                    is_hard_contract=True,
                    frequency_match=True,
                    source="csmar_metadata_probe",
                    evidence="alias命中=是",
                )
            ]
        )


class FailingMapper:
    def map_probe_bindings(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingResult:
        return VariableMappingResult(
            failure_reason="变量映射失败：核心变量 `ROA` 在 CSMAR 元数据中不可得。",
            warnings=["核心变量缺失触发 fail-fast。"],
        )


class SuccessfulProbeExecutor:
    def execute_coverage(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> ProbeCoverageResult:
        return ProbeCoverageResult(
            hard_coverage_rate=1.0,
            soft_coverage_rate=1.0,
            key_alignment_ready=True,
            target_grain_ready=True,
        )


class FailingProbeExecutor:
    def execute_coverage(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> ProbeCoverageResult:
        return ProbeCoverageResult(
            hard_coverage_rate=0.5,
            soft_coverage_rate=1.0,
            key_alignment_ready=False,
            target_grain_ready=True,
            hard_gaps=["ROA"],
            failure_reason="探针失败：Hard Contract 变量不可得：ROA。",
        )


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_range="2010-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def test_orchestrator_happy_path_pauses_at_gateway() -> None:
    """验证主工作流会在完成 S1-T6 后进入 Gateway，中断点正是人工审批入口。"""
    orchestrator = ApplicationOrchestrator(
        parser=SuccessfulParser(),
        mapper=SuccessfulMapper(),
        probe_executor=SuccessfulProbeExecutor(),
    )

    state, thread_id = orchestrator.run(_build_request())

    # 工作流在 Gateway 中断后返回当前 checkpoint 状态
    assert state.stage is RunStage.CONTRACTED
    assert state.spec is not None
    assert state.parse_result is not None
    assert state.variable_definitions is not None
    assert state.data_requirements_draft is not None
    assert state.variable_bindings is not None
    assert state.variable_mapping_result is not None
    assert state.probe_coverage_result is not None
    assert state.data_contract_bundle is not None
    assert "需求解析已完成。" in state.notes
    assert "变量定义与数据需求清单已生成。" in state.notes
    assert "CSMAR 探针级变量映射已完成。" in state.notes
    assert "探针执行与覆盖摘要已完成。" in state.notes
    assert "最低可行数据契约已生成。" in state.notes

    assert state.data_requirements_draft.entity_scope == "A股上市银行"
    assert state.data_requirements_draft.time_start_year == 2010
    assert state.data_requirements_draft.time_end_year == 2023

    item_roles = {item.role for item in state.data_requirements_draft.items}
    assert "dependent" in item_roles
    assert "independent" in item_roles
    assert "control" in item_roles

    pending_controls = [
        item for item in state.data_requirements_draft.items if item.role == "control"
    ]
    assert pending_controls
    assert all(
        item.slot_status == "pending_agent_completion" for item in pending_controls
    )
    assert state.data_contract_bundle.hard_contract_variables == [
        "ROA",
        "数字化转型指数",
    ]
    assert thread_id.startswith("run-")


def test_gateway_approve_advances_to_approved_stage() -> None:
    """验证 S1-T7 的 approve 恢复路径会锁定契约并把流程推进到 `APPROVED`。"""
    orchestrator = ApplicationOrchestrator(
        parser=SuccessfulParser(),
        mapper=SuccessfulMapper(),
        probe_executor=SuccessfulProbeExecutor(),
    )

    state, thread_id = orchestrator.run(_build_request())
    assert state.stage is RunStage.CONTRACTED

    state = orchestrator.resume(thread_id, {"decision": "approved", "reason": ""})

    assert state.stage is RunStage.APPROVED
    assert state.gateway_record is not None
    assert state.gateway_record.decision is GatewayDecision.APPROVED
    assert "Gateway 审批通过，数据契约已锁定。" in state.notes


def test_gateway_reject_fails_with_reason() -> None:
    """验证 reject 是显式人工终止分支，原因会写入审计记录并反馈到状态备注。"""
    orchestrator = ApplicationOrchestrator(
        parser=SuccessfulParser(),
        mapper=SuccessfulMapper(),
        probe_executor=SuccessfulProbeExecutor(),
    )

    state, thread_id = orchestrator.run(_build_request())
    assert state.stage is RunStage.CONTRACTED

    state = orchestrator.resume(
        thread_id, {"decision": "rejected", "reason": "变量覆盖不满足预期"}
    )

    assert state.stage is RunStage.FAILED
    assert state.gateway_record is not None
    assert state.gateway_record.decision is GatewayDecision.REJECTED
    assert state.gateway_record.reason == "变量覆盖不满足预期"
    assert "Gateway 审批被驳回：变量覆盖不满足预期" in state.notes


def test_phase1_failure_skips_gateway() -> None:
    """验证前置可行性失败时不会误进审批节点，确保 Gateway 只处理有效契约。"""
    orchestrator = ApplicationOrchestrator(parser=FailingParser())

    state, _ = orchestrator.run(_build_request())

    assert state.stage is RunStage.FAILED
    assert state.gateway_record is None
    assert state.spec is None
    assert state.parse_result is not None
    assert state.variable_definitions is None
    assert state.data_requirements_draft is None
    assert state.variable_bindings is None
    assert "需求解析失败：Tongyi 未产出可用的研究规范。" in state.notes


def test_orchestrator_fails_on_hard_contract_mapping_gap() -> None:
    """验证应用层会保留映射节点的硬失败语义，而不是吞掉 fail-fast 信息。"""
    orchestrator = ApplicationOrchestrator(
        parser=SuccessfulParser(), mapper=FailingMapper()
    )

    state, _ = orchestrator.run(_build_request())

    assert state.stage is RunStage.FAILED
    assert state.variable_mapping_result is not None
    assert state.variable_mapping_result.failure_reason is not None
    assert state.variable_bindings is None
    assert "核心变量缺失触发 fail-fast。" in state.notes


def test_orchestrator_fails_on_probe_coverage_gap() -> None:
    """验证探针覆盖失败会在最外层编排中透传，作为停止进入 Gateway 的依据。"""
    orchestrator = ApplicationOrchestrator(
        parser=SuccessfulParser(),
        mapper=SuccessfulMapper(),
        probe_executor=FailingProbeExecutor(),
    )

    state, _ = orchestrator.run(_build_request())

    assert state.stage is RunStage.FAILED
    assert state.probe_coverage_result is not None
    assert state.probe_coverage_result.failure_reason is not None
    assert "Hard Contract 变量不可得" in state.notes[-1]


def test_orchestrator_wraps_settings_errors() -> None:
    """验证启动配置错误会被包装成编排层错误，避免底层设置异常直接泄漏。"""
    def failing_settings_factory() -> Settings:
        raise SettingsError(["DASHSCOPE_API_KEY: Field required"])

    orchestrator = ApplicationOrchestrator(settings_factory=failing_settings_factory)

    try:
        orchestrator.app_name()
    except WorkflowBootstrapError as exc:
        assert exc.details == ["DASHSCOPE_API_KEY: Field required"]
    else:
        raise AssertionError("Expected WorkflowBootstrapError to be raised")

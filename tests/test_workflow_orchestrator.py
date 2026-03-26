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
    """Happy path: Phase1 成功 → 工作流命中 Gateway interrupt → 返回 CONTRACTED 状态。"""
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
    """Approve 后 stage == APPROVED，gateway_record 正确记录。"""
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
    """Reject 后 stage == FAILED，gateway_record 包含驳回原因。"""
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
    """Phase1 失败时直接到 END，不进入 Gateway 节点。"""
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
    def failing_settings_factory() -> Settings:
        raise SettingsError(["DASHSCOPE_API_KEY: Field required"])

    orchestrator = ApplicationOrchestrator(settings_factory=failing_settings_factory)

    try:
        orchestrator.app_name()
    except WorkflowBootstrapError as exc:
        assert exc.details == ["DASHSCOPE_API_KEY: Field required"]
    else:
        raise AssertionError("Expected WorkflowBootstrapError to be raised")

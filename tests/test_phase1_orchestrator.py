"""Phase 1 可行性编排测试。

该文件覆盖 `Phase1FeasibilityOrchestrator`，它把 S1-T2 到 S1-T6 串成一条
线性可行性流水线：需求解析 -> 变量清单生成 -> CSMAR 探针映射 -> 覆盖探测
-> 最低可行数据契约。它是 Gateway 之前的核心收敛层，负责把单个节点的
成功/失败统一投影到 `ResearchState.stage`。
"""

from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator
from stata_agent.workflow.ports import ProbeExecutorPort
from stata_agent.workflow.ports import RequirementParserPort
from stata_agent.workflow.ports import VariableMapperPort
from stata_agent.workflow.state import ResearchState
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


class SuccessfulBuilder:
    def build(self, spec: ResearchSpec):
        from stata_agent.services.variable_requirements_builder import (
            VariableRequirementsBuilder,
        )

        return VariableRequirementsBuilder().build(spec)


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


class SuccessfulDataContractBuilder:
    def build(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        variable_bindings: list[VariableBinding],
        probe_coverage: ProbeCoverageResult,
    ):
        from stata_agent.services.data_contract_builder import DataContractBuilder

        return DataContractBuilder().build(
            request=request,
            spec=spec,
            variable_definitions=variable_definitions,
            variable_bindings=variable_bindings,
            probe_coverage=probe_coverage,
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


def _build_orchestrator(
    parser: RequirementParserPort | None = None,
    mapper: VariableMapperPort | None = None,
    probe_executor: ProbeExecutorPort | None = None,
) -> Phase1FeasibilityOrchestrator:
    parser_impl = parser if parser is not None else SuccessfulParser()
    mapper_impl = mapper if mapper is not None else SuccessfulMapper()
    probe_executor_impl = (
        probe_executor if probe_executor is not None else SuccessfulProbeExecutor()
    )
    return Phase1FeasibilityOrchestrator(
        parser=parser_impl,
        builder=SuccessfulBuilder(),
        mapper=mapper_impl,
        probe_executor=probe_executor_impl,
        data_contract_builder=SuccessfulDataContractBuilder(),
    )


def test_phase1_runs_to_contracted_state() -> None:
    """验证 Phase 1 happy path 会收敛到 `CONTRACTED`，并带齐 Gateway 所需工件。"""
    state = _build_orchestrator().run_feasibility(
        ResearchState(request=_build_request())
    )

    assert state.stage is RunStage.CONTRACTED
    assert state.spec is not None
    assert state.parse_result is not None
    assert state.variable_definitions is not None
    assert state.data_requirements_draft is not None
    assert state.variable_bindings is not None
    assert state.variable_mapping_result is not None
    assert state.probe_coverage_result is not None
    assert state.data_contract_bundle is not None


def test_phase1_fails_on_parse_error() -> None:
    """验证最早的需求解析失败会短路整个 Phase 1，并阻止后续节点执行。"""
    state = _build_orchestrator(parser=FailingParser()).run_feasibility(
        ResearchState(request=_build_request())
    )

    assert state.stage is RunStage.FAILED
    assert state.spec is None
    assert state.parse_result is not None


def test_phase1_fails_on_mapping_gap() -> None:
    """验证 S1-T4 的硬缺口会被编排层保留为失败态，而不是伪造空绑定继续运行。"""
    state = _build_orchestrator(mapper=FailingMapper()).run_feasibility(
        ResearchState(request=_build_request())
    )

    assert state.stage is RunStage.FAILED
    assert state.variable_mapping_result is not None
    assert state.variable_bindings is None


def test_phase1_fails_on_probe_gap() -> None:
    """验证 S1-T5 的 fail-fast 结果会直接把编排推入失败态，避免生成虚假契约。"""
    state = _build_orchestrator(probe_executor=FailingProbeExecutor()).run_feasibility(
        ResearchState(request=_build_request())
    )

    assert state.stage is RunStage.FAILED
    assert state.probe_coverage_result is not None
    assert state.probe_coverage_result.failure_reason is not None

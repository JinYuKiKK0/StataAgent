"""LangSmith/共享 graph 入口 smoke tests。

该文件覆盖 `build_agent_graph` 这层薄适配器。它位于 `ApplicationOrchestrator`
之外，负责给 LangSmith 或其他 graph 入口复用统一的工作流拓扑。
测试目标是防止图定义和主编排漂移，尤其是 Gateway interrupt 位置和
Phase 1 失败分支的构造路径。
"""

from stata_agent.agent import build_agent_graph
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
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


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_range="2010-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def test_agent_graph_reuses_shared_workflow_and_interrupts_at_gateway() -> None:
    """验证共享 graph 会复用主工作流，并在 S1-T7 的 Gateway 节点停下。"""
    graph = build_agent_graph(
        parser=SuccessfulParser(),
        mapper=SuccessfulMapper(),
        probe_executor=SuccessfulProbeExecutor(),
    )

    result = graph.invoke(ResearchState(request=_build_request()))

    assert result["stage"] is RunStage.CONTRACTED
    assert result["data_contract_bundle"] is not None
    assert "__interrupt__" in result
    assert result["__interrupt__"]


def test_agent_graph_handles_phase1_failures_without_constructor_errors() -> None:
    """验证图入口在 Phase 1 失败时仍能稳定收敛到失败态，而不是在构造期崩溃。"""
    graph = build_agent_graph(parser=FailingParser())

    result = graph.invoke(ResearchState(request=_build_request()))

    assert result["stage"] is RunStage.FAILED
    assert result["parse_result"] is not None
    assert "需求解析失败：Tongyi 未产出可用的研究规范。" in result["notes"]

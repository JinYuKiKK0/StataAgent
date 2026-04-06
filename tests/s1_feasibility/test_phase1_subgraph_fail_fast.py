# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false

"""S1 Phase 1 子图 fail-fast 测试。"""

from collections.abc import Iterable

from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.types import RunStage

from tests.s1_feasibility.phase1_subgraph_artifacts import build_builder_result
from tests.s1_feasibility.phase1_subgraph_artifacts import build_probe_results
from tests.s1_feasibility.phase1_subgraph_artifacts import build_request
from tests.s1_feasibility.phase1_subgraph_support import build_orchestrator


def _collect_update_order(chunks: Iterable[object]) -> list[str]:
    order: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict) or chunk.get("type") != "updates":
            continue
        data = chunk.get("data")
        if not isinstance(data, dict) or not data:
            continue
        order.append(next(iter(data)))
    return order


def test_phase1_subgraph_stops_after_parse_failure() -> None:
    """验证 parse 失败时子图会在首节点后终止。"""
    orchestrator = build_orchestrator(
        parse_result=RequirementParseResult(
            spec=None,
            failure_reason="需求解析失败：无法生成研究规范。",
            warnings=["需求解析失败：无法生成研究规范。"],
        )
    )

    chunks = orchestrator.compiled_graph.stream(
        ResearchState(request=build_request()),
        stream_mode="updates",
        version="v2",
    )
    final_state = orchestrator.run_feasibility(ResearchState(request=build_request()))

    assert _collect_update_order(chunks) == ["parse_request"]
    assert final_state.stage is RunStage.FAILED
    assert set(final_state.node_audits) == {"parse_request"}


def test_phase1_subgraph_stops_after_materialization_failure() -> None:
    """验证映射物化失败时不会继续执行 probe 节点。"""
    orchestrator = build_orchestrator(
        mapping_result=VariableMappingResult(
            bindings=[],
            failure_reason="变量映射失败：核心变量 `ROA` 在当前预算内未能映射到 CSMAR 字段。",
            hard_contract_variables=["ROA", "资本充足率"],
            warnings=["核心变量缺失触发 fail-fast。"],
            resolved_variable_definitions=build_builder_result().variable_definitions,
        )
    )

    chunks = orchestrator.compiled_graph.stream(
        ResearchState(request=build_request()),
        stream_mode="updates",
        version="v2",
    )

    assert _collect_update_order(chunks) == [
        "parse_request",
        "build_variable_requirements",
        "plan_probe_mapping",
        "materialize_variable_bindings",
    ]


def test_phase1_subgraph_stops_after_probe_summary_failure() -> None:
    """验证 probe 摘要失败时不会继续构建数据契约。"""
    orchestrator = build_orchestrator(
        coverage_result=ProbeCoverageResult(
            probe_results=build_probe_results(),
            hard_coverage_rate=0.5,
            soft_coverage_rate=1.0,
            hard_gaps=["ROA"],
            key_alignment_ready=False,
            target_grain_ready=True,
            warnings=["探针摘要已生成。"],
            failure_reason="探针失败：Hard Contract 变量不可得：ROA。",
        )
    )

    chunks = orchestrator.compiled_graph.stream(
        ResearchState(request=build_request()),
        stream_mode="updates",
        version="v2",
    )

    assert _collect_update_order(chunks) == [
        "parse_request",
        "build_variable_requirements",
        "plan_probe_mapping",
        "materialize_variable_bindings",
        "run_field_probes",
        "summarize_probe_coverage",
    ]

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false

"""S1 Phase 1 子图 happy path 测试。"""

from collections.abc import Iterable

from stata_agent.workflow.state import ResearchState

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


def test_phase1_subgraph_streams_all_seven_nodes_on_happy_path() -> None:
    """验证 S1 子图 happy path 会显式流出全部七个节点。"""
    orchestrator = build_orchestrator()

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
        "build_data_contract",
    ]

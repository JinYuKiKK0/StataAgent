from __future__ import annotations

from stata_agent.services.mapping.contracts import VariableMappingResult
from stata_agent.services.probe.contracts import ProbeCoverageResult
from stata_agent.workflow.stages.phase1_audit import build_workflow_audit
from stata_agent.workflow.stages.phase1_audit import trace_ids_from_bindings
from stata_agent.workflow.stages.phase1_audit import trace_ids_from_probe_results
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.state_contracts import Phase1StateUpdate
from stata_agent.workflow.types import RunStage


def build_mapping_state_update(
    state: ResearchState,
    mapping_result: VariableMappingResult,
) -> Phase1StateUpdate:
    notes = list(state.workflow_audit.notes)
    notes.extend(mapping_result.warnings)
    phase1 = state.phase1_artifacts.model_copy(update={"mapping_result": mapping_result})
    updates: Phase1StateUpdate = {
        "phase1_artifacts": phase1,
        "workflow_audit": build_workflow_audit(
            state,
            notes=notes,
            node_name="materialize_variable_bindings",
            input_summary={
                "planned_items_count": len(state.phase1_artifacts.mapping_plan_result.items)
                if state.phase1_artifacts.mapping_plan_result is not None
                else 0,
            },
            output_summary={
                "bindings_count": len(mapping_result.bindings),
                "soft_contract_gaps_count": len(mapping_result.soft_contract_gaps),
            },
            warnings=list(mapping_result.warnings),
            failure_reason=mapping_result.failure_reason,
            trace_ids=trace_ids_from_bindings(mapping_result.bindings),
        ),
    }
    if mapping_result.failure_reason is not None:
        notes.append(mapping_result.failure_reason)
        updates["stage"] = RunStage.FAILED
        updates["workflow_audit"] = updates["workflow_audit"].model_copy(update={"notes": notes})
        return updates

    notes.append("CSMAR 探针级变量映射已完成。")
    resolved_definitions = mapping_result.resolved_variable_definitions
    if not resolved_definitions:
        assert state.phase1_artifacts.variable_definitions is not None
        resolved_definitions = state.phase1_artifacts.variable_definitions
    updates["phase1_artifacts"] = phase1.model_copy(
        update={
            "variable_definitions": resolved_definitions,
            "variable_bindings": mapping_result.bindings,
        }
    )
    updates["stage"] = RunStage.MAPPED
    updates["workflow_audit"] = updates["workflow_audit"].model_copy(update={"notes": notes})
    return updates


def build_probe_summary_state_update(
    state: ResearchState,
    coverage_result: ProbeCoverageResult,
) -> Phase1StateUpdate:
    notes = list(state.workflow_audit.notes)
    notes.extend(coverage_result.warnings)
    updates: Phase1StateUpdate = {
        "phase1_artifacts": state.phase1_artifacts.model_copy(
            update={"probe_coverage_result": coverage_result}
        ),
        "workflow_audit": build_workflow_audit(
            state,
            notes=notes,
            node_name="summarize_probe_coverage",
            input_summary={
                "probe_results_count": len(state.phase1_artifacts.probe_results_raw or [])
            },
            output_summary={
                "hard_gaps_count": len(coverage_result.hard_gaps),
                "soft_gaps_count": len(coverage_result.soft_gaps),
                "hard_coverage_rate": coverage_result.hard_coverage_rate,
                "soft_coverage_rate": coverage_result.soft_coverage_rate,
            },
            warnings=list(coverage_result.warnings),
            failure_reason=coverage_result.failure_reason,
            trace_ids=trace_ids_from_probe_results(coverage_result.probe_results),
        ),
    }
    if coverage_result.failure_reason is not None:
        notes.append(coverage_result.failure_reason)
        updates["stage"] = RunStage.FAILED
        updates["workflow_audit"] = updates["workflow_audit"].model_copy(update={"notes": notes})
        return updates

    notes.append("探针执行与覆盖摘要已完成。")
    updates["stage"] = RunStage.PROBED
    updates["workflow_audit"] = updates["workflow_audit"].model_copy(update={"notes": notes})
    return updates

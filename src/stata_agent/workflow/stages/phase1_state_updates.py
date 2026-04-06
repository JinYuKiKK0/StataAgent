from __future__ import annotations

from stata_agent.services.mapping.contracts import VariableMappingResult
from stata_agent.services.probe.contracts import ProbeCoverageResult
from stata_agent.workflow.stages.phase1_audit import build_workflow_audit
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.state_contracts import Phase1StateUpdate
from stata_agent.workflow.types import RunStage


def build_mapping_state_update(
    state: ResearchState,
    mapping_result: VariableMappingResult,
    *,
    planned_items_count: int,
    audit_refs: list[str] | None = None,
) -> Phase1StateUpdate:
    notes = list(state.workflow_audit.notes)
    notes.extend(mapping_result.warnings)
    updates: Phase1StateUpdate = {
        "phase1_artifacts": state.phase1_artifacts,
        "workflow_audit": build_workflow_audit(
            state,
            notes=notes,
            node_name="materialize_variable_bindings",
            input_summary={
                "planned_items_count": planned_items_count,
            },
            output_summary={
                "bindings_count": len(mapping_result.bindings),
                "soft_contract_gaps_count": len(mapping_result.soft_contract_gaps),
            },
            warnings=list(mapping_result.warnings),
            failure_reason=mapping_result.failure_reason,
            audit_refs=audit_refs,
        ),
    }
    if mapping_result.failure_reason is not None:
        notes.append(mapping_result.failure_reason)
        updates["stage"] = RunStage.FAILED
        updates["workflow_audit"] = updates["workflow_audit"].model_copy(update={"notes": notes})
        return updates

    notes.append("CSMAR 探针级变量映射已完成。")
    updates["phase1_artifacts"] = state.phase1_artifacts.model_copy(
        update={
            "variable_bindings": mapping_result.bindings,
        }
    )
    updates["stage"] = RunStage.MAPPED
    updates["workflow_audit"] = updates["workflow_audit"].model_copy(update={"notes": notes})
    return updates


def build_probe_summary_state_update(
    state: ResearchState,
    coverage_result: ProbeCoverageResult,
    *,
    audit_refs: list[str] | None = None,
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
            input_summary={"probe_results_count": len(coverage_result.probe_results)},
            output_summary={
                "hard_gaps_count": len(coverage_result.hard_gaps),
                "soft_gaps_count": len(coverage_result.soft_gaps),
                "hard_coverage_rate": coverage_result.hard_coverage_rate,
                "soft_coverage_rate": coverage_result.soft_coverage_rate,
            },
            warnings=list(coverage_result.warnings),
            failure_reason=coverage_result.failure_reason,
            audit_refs=audit_refs,
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

from __future__ import annotations

from typing import cast

from stata_agent.services.audit.ports import AuditStorePort
from stata_agent.services.mapping.contracts import MappingPlannerInput
from stata_agent.services.mapping.contracts import VariableMappingPlanResult
from stata_agent.services.probe.contracts import ProbeExecutionInput
from stata_agent.services.probe.contracts import VariableProbeResult
from stata_agent.workflow.state import ResearchState


def build_mapping_planner_input(state: ResearchState) -> MappingPlannerInput | None:
    spec = state.phase1_artifacts.spec
    variable_definitions = state.phase1_artifacts.variable_definitions
    if spec is None or variable_definitions is None:
        return None
    return MappingPlannerInput(
        topic=spec.topic,
        entity_scope=spec.entity_scope,
        time_start_year=spec.time_start_year,
        time_end_year=spec.time_end_year,
        analysis_frequency_hint=spec.analysis_frequency_hint,
        analysis_grain_candidates=list(spec.analysis_grain_candidates),
        variable_definitions=variable_definitions,
    )


def build_probe_execution_input(state: ResearchState) -> ProbeExecutionInput | None:
    spec = state.phase1_artifacts.spec
    variable_bindings = state.phase1_artifacts.variable_bindings
    if spec is None or variable_bindings is None:
        return None
    return ProbeExecutionInput(
        entity_scope=spec.entity_scope,
        analysis_grain=spec.analysis_grain_candidates[0]
        if spec.analysis_grain_candidates
        else "",
        time_start_year=spec.time_start_year,
        time_end_year=spec.time_end_year,
        variable_bindings=variable_bindings,
    )


def load_mapping_plan_result(
    *,
    state: ResearchState,
    audit_store: AuditStorePort,
    thread_id: str,
) -> VariableMappingPlanResult | None:
    audit_ref = _latest_audit_ref(state, "plan_probe_mapping")
    if audit_ref is None:
        return None
    audit_record = audit_store.read_audit(thread_id=thread_id, audit_ref=audit_ref)
    if audit_record is None:
        return None
    payload = audit_record.payload.get("planning_result")
    if not isinstance(payload, dict):
        return None
    return VariableMappingPlanResult.model_validate(payload)


def load_probe_results(
    *,
    state: ResearchState,
    audit_store: AuditStorePort,
    thread_id: str,
) -> list[VariableProbeResult] | None:
    audit_ref = _latest_audit_ref(state, "run_field_probes")
    if audit_ref is None:
        return None
    audit_record = audit_store.read_audit(thread_id=thread_id, audit_ref=audit_ref)
    if audit_record is None:
        return None
    payload = audit_record.payload.get("probe_results")
    if not isinstance(payload, list):
        return None
    return [
        VariableProbeResult.model_validate(item)
        for item in cast(list[object], payload)
    ]


def _latest_audit_ref(state: ResearchState, node_name: str) -> str | None:
    node_audit = state.workflow_audit.node_audits.get(node_name)
    if node_audit is None or not node_audit.audit_refs:
        return None
    return node_audit.audit_refs[-1]

from __future__ import annotations

from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.services.spec.contracts import DataRequirementItem
from stata_agent.services.spec.contracts import DataRequirementsDraft
from stata_agent.services.spec.contracts import VariableRequirementsResult


class VariableRequirementsBuilder:
    def build(self, spec: ResearchSpec) -> VariableRequirementsResult:
        definitions = _build_definitions(spec)
        requirements = DataRequirementsDraft(
            entity_scope=spec.entity_scope,
            time_start_year=spec.time_start_year,
            time_end_year=spec.time_end_year,
            items=[_to_requirement_item(definition) for definition in definitions],
        )
        return VariableRequirementsResult(
            variable_definitions=definitions,
            data_requirements_draft=requirements,
            warnings=[],
        )


def _build_definitions(spec: ResearchSpec) -> list[VariableDefinition]:
    definitions: list[VariableDefinition] = []
    definitions.append(_build_core_variable(spec, spec.dependent_variable, "dependent"))
    definitions.extend(
        _build_core_variable(spec, value, "independent")
        for value in spec.independent_variables
    )
    definitions.extend(_build_control_variables(spec))
    return definitions


def _build_core_variable(
    spec: ResearchSpec, variable_name: str, role: str
) -> VariableDefinition:
    cleaned_name = variable_name.strip()
    return VariableDefinition(
        variable_name=cleaned_name,
        role=role,
        is_locked=True,
        slot_status="ready",
        frequency_hint=spec.analysis_frequency_hint,
        note=None,
    )


def _build_control_variables(spec: ResearchSpec) -> list[VariableDefinition]:
    normalized_controls = _normalize_controls(spec)
    return [
        VariableDefinition(
            variable_name=control,
            role="control",
            is_locked=_is_user_required(spec, control),
            slot_status="pending_agent_completion",
            frequency_hint=spec.analysis_frequency_hint,
            note=_build_control_note(spec, control),
        )
        for control in normalized_controls
    ]


def _normalize_controls(spec: ResearchSpec) -> list[str]:
    forbidden = {
        spec.dependent_variable.strip(),
        *[value.strip() for value in spec.independent_variables],
    }
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in spec.control_variable_candidates:
        cleaned = candidate.strip()
        if not cleaned or cleaned in seen or cleaned in forbidden:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
    return normalized


def _to_requirement_item(definition: VariableDefinition) -> DataRequirementItem:
    return DataRequirementItem(
        variable_name=definition.variable_name,
        role=definition.role,
        frequency_hint=definition.frequency_hint,
        slot_status=definition.slot_status,
    )


def _is_user_required(spec: ResearchSpec, variable_name: str) -> bool:
    empirical_text = spec.empirical_requirements.strip()
    if not empirical_text:
        return False
    return variable_name in empirical_text


def _build_control_note(spec: ResearchSpec, variable_name: str) -> str:
    if _is_user_required(spec, variable_name):
        return "用户显式要求的关键变量，后续不得自动剔除。"
    return "控制变量候选，待 agent 在建模阶段确认纳入。"

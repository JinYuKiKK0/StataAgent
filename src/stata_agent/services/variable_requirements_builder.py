from __future__ import annotations

from stata_agent.domains.spec.types import DataRequirementItem
from stata_agent.domains.spec.types import DataRequirementsDraft
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.domains.spec.types import VariableRequirementsResult


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
    definitions.extend(_build_core_variable(spec, value, "independent") for value in spec.independent_variables)
    definitions.extend(_build_control_variables(spec))
    return definitions


def _build_core_variable(spec: ResearchSpec, variable_name: str, role: str) -> VariableDefinition:
    cleaned_name = variable_name.strip()
    return VariableDefinition(
        variable_name=cleaned_name,
        role=role,
        is_locked=True,
        slot_status="ready",
        frequency_hint=_infer_frequency_hint(spec.topic, cleaned_name),
        source_domain_hint=_infer_source_domain_hint(spec.entity_scope, cleaned_name),
        note=None,
    )


def _build_control_variables(spec: ResearchSpec) -> list[VariableDefinition]:
    normalized_controls = _normalize_controls(spec)
    return [
        VariableDefinition(
            variable_name=control,
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint=_infer_frequency_hint(spec.topic, control),
            source_domain_hint=_infer_source_domain_hint(spec.entity_scope, control),
            note="控制变量候选，待 agent 在建模阶段确认纳入。",
        )
        for control in normalized_controls
    ]


def _normalize_controls(spec: ResearchSpec) -> list[str]:
    forbidden = {spec.dependent_variable.strip(), *[value.strip() for value in spec.independent_variables]}
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
        source_domain_hint=definition.source_domain_hint,
        slot_status=definition.slot_status,
    )


def _infer_frequency_hint(topic: str, variable_name: str) -> str:
    text = f"{topic} {variable_name}".strip().lower()
    if _contains_any(text, ["月", "month", "monthly", "m1", "m2", "m3"]):
        return "monthly"
    if _contains_any(text, ["季", "季度", "quarter", "quarterly", "q1", "q2", "q3", "q4"]):
        return "quarterly"
    if _contains_any(text, ["年", "年度", "annual", "yearly"]):
        return "annual"
    return "unknown"


def _infer_source_domain_hint(entity_scope: str, variable_name: str) -> str:
    text = f"{entity_scope} {variable_name}".strip().lower()
    if _contains_any(text, ["银行", "bank", "资本充足", "不良贷款", "拨备"]):
        return "bank_financials"
    if _contains_any(text, ["gdp", "cpi", "m2", "利率", "失业率", "通胀"]):
        return "macro_economy"
    if _contains_any(text, ["收益率", "波动率", "市值", "换手率", "beta"]):
        return "market_trading"
    if _contains_any(text, ["a股", "上市公司", "企业", "firm", "company"]):
        return "firm_financials"
    return "unknown"


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)

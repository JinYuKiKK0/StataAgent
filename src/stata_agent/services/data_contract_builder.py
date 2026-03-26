from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition


class DataContractBuilder:
    def build(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        variable_bindings: list[VariableBinding],
        probe_coverage: ProbeCoverageResult,
    ) -> DataContractBundle:
        hard_variables = _collect_hard_variables(variable_definitions)
        soft_variables = _collect_soft_variables(variable_definitions)
        allowed_soft_removals = _collect_allowed_soft_removals(soft_variables, probe_coverage)
        substitution_log = _collect_substitution_log(variable_bindings)
        residual_risks = _collect_residual_risks(probe_coverage)

        _assert_core_variables_protected(spec, hard_variables, allowed_soft_removals)

        return DataContractBundle(
            hard_contract_variables=hard_variables,
            soft_contract_variables=soft_variables,
            allowed_soft_removals=allowed_soft_removals,
            analysis_grain=_pick_analysis_grain(spec),
            entity_scope=spec.entity_scope,
            time_start_year=spec.time_start_year,
            time_end_year=spec.time_end_year,
            empirical_requirements=request.empirical_requirements,
            variable_definitions=variable_definitions,
            variable_bindings=variable_bindings,
            probe_coverage=probe_coverage,
            substitution_log=substitution_log,
            residual_risks=residual_risks,
            spec=spec,
        )


def _collect_hard_variables(variable_definitions: list[VariableDefinition]) -> list[str]:
    return [item.variable_name for item in variable_definitions if item.is_locked]


def _collect_soft_variables(variable_definitions: list[VariableDefinition]) -> list[str]:
    return [item.variable_name for item in variable_definitions if not item.is_locked]


def _collect_allowed_soft_removals(
    soft_variables: list[str],
    probe_coverage: ProbeCoverageResult,
) -> list[str]:
    soft_set = set(soft_variables)
    return [name for name in probe_coverage.soft_gaps if name in soft_set]


def _collect_substitution_log(variable_bindings: list[VariableBinding]) -> list[str]:
    records: list[str] = []
    for binding in variable_bindings:
        if binding.substituted_from is None:
            continue
        records.append(f"{binding.substituted_from} -> {binding.variable_name} ({binding.table_name}.{binding.field_name})")
    return records


def _collect_residual_risks(probe_coverage: ProbeCoverageResult) -> list[str]:
    risks: list[str] = []
    if probe_coverage.soft_gaps:
        soft_text = "、".join(probe_coverage.soft_gaps)
        risks.append(f"Soft Contract 变量覆盖不足：{soft_text}。")
    if not probe_coverage.key_alignment_ready:
        risks.append("关键主键仍存在对齐风险。")
    if not probe_coverage.target_grain_ready:
        risks.append("目标分析粒度存在可得性风险。")
    return risks


def _assert_core_variables_protected(
    spec: ResearchSpec,
    hard_variables: list[str],
    allowed_soft_removals: list[str],
) -> None:
    protected = {spec.dependent_variable, *spec.independent_variables, *hard_variables}
    leaked = [name for name in allowed_soft_removals if name in protected]
    if leaked:
        joined = "、".join(leaked)
        raise ValueError(f"核心变量不能进入允许自动剔除列表：{joined}。")


def _pick_analysis_grain(spec: ResearchSpec) -> str:
    if not spec.analysis_grain_candidates:
        return ""
    return spec.analysis_grain_candidates[0]

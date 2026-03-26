from stata_agent.domains.mapping.ports import CsmarMetadataProviderPort
from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.providers.csmar import CsmarMetadataError


class VariableMapper:
    def __init__(self, metadata_provider: CsmarMetadataProviderPort) -> None:
        self._metadata_provider = metadata_provider

    def map_probe_bindings(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingResult:
        hard_variables = self._build_hard_variables(request, spec, variable_definitions)
        bindings: list[VariableBinding] = []
        soft_gaps: list[str] = []

        for definition in variable_definitions:
            mapping = self._map_single_variable(definition, hard_variables)
            if mapping is not None:
                bindings.append(mapping)
                continue
            if definition.variable_name in hard_variables:
                return VariableMappingResult(
                    failure_reason=f"变量映射失败：核心变量 `{definition.variable_name}` 在 CSMAR 元数据中不可得。",
                    hard_contract_variables=sorted(hard_variables),
                    warnings=["核心变量缺失触发 fail-fast。"],
                )
            soft_gaps.append(definition.variable_name)

        return VariableMappingResult(
            bindings=bindings,
            hard_contract_variables=sorted(hard_variables),
            soft_contract_gaps=soft_gaps,
            warnings=self._build_soft_gap_warnings(soft_gaps),
        )

    def _build_hard_variables(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> set[str]:
        hard_variables = {spec.dependent_variable, *spec.independent_variables}
        empirical_text = request.empirical_requirements.strip()
        if not empirical_text:
            return hard_variables
        for definition in variable_definitions:
            if definition.variable_name in empirical_text:
                hard_variables.add(definition.variable_name)
        return hard_variables

    def _map_single_variable(
        self,
        definition: VariableDefinition,
        hard_variables: set[str],
    ) -> VariableBinding | None:
        try:
            candidates = self._metadata_provider.find_field_candidates(definition.variable_name)
        except CsmarMetadataError:
            return None
        if not candidates:
            return None

        best = self._select_best_candidate(candidates, definition.frequency_hint)
        if best is None:
            return None
        if not self._metadata_provider.field_exists(best.table_name, best.field_name):
            return None

        is_hard = definition.variable_name in hard_variables
        confidence = self._compute_confidence(best, definition.frequency_hint)
        return VariableBinding(
            variable_name=definition.variable_name,
            table_name=best.table_name,
            field_name=best.field_name,
            confidence=confidence,
            csmar_database=best.csmar_database,
            contract_tier="hard" if is_hard else "soft",
            is_hard_contract=is_hard,
            frequency_match=definition.frequency_hint in best.frequency_tags,
            source="csmar_metadata_probe",
            evidence=self._build_evidence(best, definition.frequency_hint),
        )

    def _select_best_candidate(
        self,
        candidates: list[CsmarFieldCandidate],
        frequency_hint: str,
    ) -> CsmarFieldCandidate | None:
        scored = sorted(
            candidates,
            key=lambda item: (
                frequency_hint in item.frequency_tags,
                item.alias_hit,
            ),
            reverse=True,
        )
        return scored[0] if scored else None

    def _compute_confidence(self, candidate: CsmarFieldCandidate, frequency_hint: str) -> float:
        score = 0.5
        if candidate.alias_hit:
            score += 0.3
        if frequency_hint in candidate.frequency_tags:
            score += 0.2
        return min(score, 1.0)

    def _build_evidence(self, candidate: CsmarFieldCandidate, frequency_hint: str) -> str:
        frequency_ok = "是" if frequency_hint in candidate.frequency_tags else "否"
        alias_ok = "是" if candidate.alias_hit else "否"
        return f"alias命中={alias_ok}; frequency匹配={frequency_ok}; 候选字段={candidate.field_name}"

    def _build_soft_gap_warnings(self, soft_gaps: list[str]) -> list[str]:
        if not soft_gaps:
            return []
        soft_text = "、".join(soft_gaps)
        return [f"Soft Contract 变量暂未映射：{soft_text}。"]

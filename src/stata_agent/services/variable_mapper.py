from __future__ import annotations

from typing import cast

from stata_agent.domains.mapping.ports import CsmarMetadataProviderPort
from stata_agent.domains.mapping.ports import VariableSemanticJudgePort
from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import CsmarToolTrace
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingBudget
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.providers.csmar import CsmarMetadataError
from stata_agent.services.mapping_candidate_builder import MappingCandidateBuilder


class VariableMapper:
    def __init__(
        self,
        metadata_provider: CsmarMetadataProviderPort,
        semantic_judge: VariableSemanticJudgePort | None = None,
        mapping_budget: VariableMappingBudget | None = None,
    ) -> None:
        self._metadata_provider = metadata_provider
        self._semantic_judge = semantic_judge
        self._mapping_budget = mapping_budget or VariableMappingBudget()
        self._candidate_builder = MappingCandidateBuilder(
            metadata_provider=metadata_provider,
            mapping_budget=self._mapping_budget,
        )
        self._pending_traces: list[CsmarToolTrace] = []

    def map_probe_bindings(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingResult:
        self._pending_traces = []
        hard_variables = self._build_hard_variables(request, spec, variable_definitions)
        bindings: list[VariableBinding] = []
        resolved_definitions: list[VariableDefinition] = []
        soft_gaps: list[str] = []
        warnings: list[str] = []

        for definition in variable_definitions:
            resolved_definition, binding, mapping_warnings = self._map_single_variable(
                request=request,
                spec=spec,
                definition=definition,
                is_hard=definition.variable_name in hard_variables,
            )
            resolved_definitions.append(resolved_definition)
            warnings.extend(mapping_warnings)
            if binding is not None:
                bindings.append(binding)
                continue
            if definition.variable_name in hard_variables:
                return VariableMappingResult(
                    failure_reason=(
                        f"变量映射失败：核心变量 `{definition.variable_name}` "
                        "在 CSMAR 元数据中不可得。"
                    ),
                    hard_contract_variables=sorted(hard_variables),
                    warnings=["核心变量缺失触发 fail-fast。", *warnings],
                    resolved_variable_definitions=resolved_definitions,
                )
            soft_gaps.append(definition.variable_name)

        warnings.extend(self._build_soft_gap_warnings(soft_gaps))
        return VariableMappingResult(
            bindings=bindings,
            hard_contract_variables=sorted(hard_variables),
            soft_contract_gaps=soft_gaps,
            warnings=warnings,
            resolved_variable_definitions=resolved_definitions,
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
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        definition: VariableDefinition,
        is_hard: bool,
    ) -> tuple[VariableDefinition, VariableBinding | None, list[str]]:
        variable_traces: list[CsmarToolTrace] = []
        try:
            candidates, warnings = self._candidate_builder.collect(
                spec=spec,
                definition=definition,
            )
        except CsmarMetadataError as exc:
            variable_traces = self._drain_provider_traces()
            self._pending_traces.extend(variable_traces)
            return definition, None, [str(exc)]

        variable_traces = self._drain_provider_traces()
        self._pending_traces.extend(variable_traces)

        if not candidates:
            return definition, None, warnings

        selected, judge_warning, used_semantic_judge = self._choose_candidate(
            request=request,
            spec=spec,
            definition=definition,
            candidates=candidates,
        )
        if judge_warning is not None:
            warnings.append(judge_warning)
        if selected is None:
            return definition, None, warnings

        resolved_domain = selected.database_name or "pending_resolution"
        resolved_definition = definition.model_copy(
            update={"source_domain_hint": resolved_domain}
        )
        confidence = self._compute_confidence(selected, definition.frequency_hint)
        trace_id = variable_traces[-1].trace_id if variable_traces else ""
        return (
            resolved_definition,
            VariableBinding(
                variable_name=definition.variable_name,
                table_code=selected.table_code,
                field_name=selected.field_name,
                confidence=confidence,
                database_name=resolved_domain,
                contract_tier="hard" if is_hard else "soft",
                is_hard_contract=is_hard,
                frequency_match=definition.frequency_hint in selected.frequency_tags,
                source=(
                    "csmar_semantic_judge"
                    if used_semantic_judge
                    else "csmar_metadata_probe"
                ),
                evidence=self._build_evidence(selected, definition.frequency_hint),
                trace_id=trace_id,
                table_name=selected.table_name,
                table_label=selected.table_label,
                field_label=selected.field_label,
            ),
            warnings,
        )

    def _choose_candidate(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        definition: VariableDefinition,
        candidates: list[CsmarFieldCandidate],
    ) -> tuple[CsmarFieldCandidate | None, str | None, bool]:
        if self._semantic_judge is None:
            return self._fallback_candidate(candidates, definition.frequency_hint), None, False
        try:
            decision = self._semantic_judge.judge(
                request=request,
                spec=spec,
                definition=definition,
                candidates=candidates,
            )
        except Exception as exc:
            return (
                self._fallback_candidate(candidates, definition.frequency_hint),
                f"变量 `{definition.variable_name}` 的语义判别失败，已回退启发式匹配：{exc}",
                False,
            )

        if not decision.matched:
            return (
                self._fallback_candidate(candidates, definition.frequency_hint),
                f"变量 `{definition.variable_name}` 的语义判别未命中，已回退启发式匹配。",
                False,
            )

        for candidate in candidates:
            if (
                candidate.table_code == decision.selected_table_code
                and candidate.field_name == decision.selected_field_name
            ):
                return candidate, None, True

        return (
            self._fallback_candidate(candidates, definition.frequency_hint),
            f"变量 `{definition.variable_name}` 的语义判别结果未在候选中找到，已回退启发式匹配。",
            False,
        )

    def _fallback_candidate(
        self,
        candidates: list[CsmarFieldCandidate],
        frequency_hint: str,
    ) -> CsmarFieldCandidate | None:
        scored = sorted(
            candidates,
            key=lambda item: (
                item.alias_hit,
                frequency_hint in item.frequency_tags,
                bool(item.field_label),
                len(item.match_evidence),
            ),
            reverse=True,
        )
        return scored[0] if scored else None

    def _compute_confidence(
        self, candidate: CsmarFieldCandidate, frequency_hint: str
    ) -> float:
        score = 0.45
        if candidate.alias_hit:
            score += 0.25
        if frequency_hint in candidate.frequency_tags:
            score += 0.15
        if candidate.field_label:
            score += 0.1
        if candidate.match_evidence:
            score += 0.05
        return min(score, 1.0)

    def _build_evidence(
        self, candidate: CsmarFieldCandidate, frequency_hint: str
    ) -> str:
        frequency_ok = "是" if frequency_hint in candidate.frequency_tags else "否"
        alias_ok = "是" if candidate.alias_hit else "否"
        reasons = " | ".join(candidate.match_evidence) if candidate.match_evidence else "无"
        return (
            f"alias命中={alias_ok}; frequency匹配={frequency_ok}; "
            f"候选字段={candidate.field_name}; 证据={reasons}"
        )

    def _build_soft_gap_warnings(self, soft_gaps: list[str]) -> list[str]:
        if not soft_gaps:
            return []
        soft_text = "、".join(soft_gaps)
        return [f"Soft Contract 变量暂未映射：{soft_text}。"]

    def drain_tool_traces(self) -> list[CsmarToolTrace]:
        traces = list(self._pending_traces)
        self._pending_traces.clear()
        return traces

    def _drain_provider_traces(self) -> list[CsmarToolTrace]:
        drain = getattr(self._metadata_provider, "drain_tool_traces", None)
        if not callable(drain):
            return []

        raw_traces_obj = drain()
        if not isinstance(raw_traces_obj, list):
            return []
        raw_traces = cast(list[object], raw_traces_obj)

        normalized: list[CsmarToolTrace] = []
        for item in raw_traces:
            if isinstance(item, CsmarToolTrace):
                normalized.append(item)
                continue
            try:
                normalized.append(CsmarToolTrace.model_validate(item))
            except Exception:
                continue

        return normalized

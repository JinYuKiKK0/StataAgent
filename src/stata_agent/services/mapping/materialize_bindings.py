from __future__ import annotations

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.services.mapping.contracts import VariableMappingPlanItem
from stata_agent.services.mapping.contracts import VariableMappingPlanResult
from stata_agent.services.mapping.contracts import VariableMappingResult


class VariableBindingMaterializer:
    def materialize_variable_bindings(
        self,
        *,
        variable_definitions: list[VariableDefinition],
        planning_result: VariableMappingPlanResult,
    ) -> VariableMappingResult:
        if planning_result.failure_reason is not None:
            return VariableMappingResult(
                failure_reason=planning_result.failure_reason,
                warnings=list(planning_result.warnings),
            )

        items_by_name = {
            item.variable_name: item for item in planning_result.items if item.variable_name
        }
        bindings: list[VariableBinding] = []
        soft_gaps: list[str] = []
        warnings = list(planning_result.warnings)

        for definition in variable_definitions:
            plan_item = items_by_name.get(definition.variable_name)
            is_hard = definition.is_locked
            if self._is_valid_match(plan_item):
                assert plan_item is not None
                bindings.append(self._to_binding(plan_item, definition, is_hard))
                continue

            warnings.extend(self._build_unmatched_warnings(definition.variable_name, plan_item))
            if is_hard:
                return VariableMappingResult(
                    failure_reason=(
                        f"变量映射失败：核心变量 `{definition.variable_name}` "
                        "在当前预算内未能映射到 CSMAR 字段。"
                    ),
                    warnings=["核心变量缺失触发 fail-fast。", *warnings],
                )
            soft_gaps.append(definition.variable_name)

        warnings.extend(self._build_soft_gap_warnings(soft_gaps))
        return VariableMappingResult(
            bindings=bindings,
            soft_contract_gaps=soft_gaps,
            warnings=warnings,
        )

    def _is_valid_match(self, item: VariableMappingPlanItem | None) -> bool:
        if item is None or not item.matched:
            return False
        return bool(item.table_code.strip() and item.field_name.strip())

    def _to_binding(
        self,
        item: VariableMappingPlanItem,
        definition: VariableDefinition,
        is_hard: bool,
    ) -> VariableBinding:
        return VariableBinding(
            variable_name=definition.variable_name,
            table_code=item.table_code,
            field_name=item.field_name,
            contract_tier="hard" if is_hard else "soft",
            frequency_match=item.frequency_match,
        )

    def _build_unmatched_warnings(
        self,
        variable_name: str,
        plan_item: VariableMappingPlanItem | None,
    ) -> list[str]:
        if plan_item is None:
            return [f"变量 `{variable_name}` 未收到 LLM 映射结果。"]
        if plan_item.rationale:
            return [f"变量 `{variable_name}` 未映射：{plan_item.rationale}"]
        return [f"变量 `{variable_name}` 在当前预算内未确认到字段。"]

    def _build_soft_gap_warnings(self, soft_gaps: list[str]) -> list[str]:
        if not soft_gaps:
            return []
        soft_text = "、".join(soft_gaps)
        return [f"Soft Contract 变量暂未映射：{soft_text}。"]

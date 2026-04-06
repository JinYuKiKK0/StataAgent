from __future__ import annotations

from typing import cast

from stata_agent.services.mapping.contracts import MappingPlannerInput
from stata_agent.services.mapping.contracts import VariableMappingBudget
from stata_agent.services.mapping.contracts import VariableMappingPlanResult
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.mapping.ports import MappingPlannerPort
from stata_agent.services.mapping.ports import MappingProviderScopePort


class ProbeMappingPlanner:
    def __init__(
        self,
        metadata_provider: CsmarMetadataProviderPort,
        planner: MappingPlannerPort,
        scope_factory: MappingProviderScopePort,
        mapping_budget: VariableMappingBudget | None = None,
    ) -> None:
        self._metadata_provider = metadata_provider
        self._planner = planner
        self._scope_factory = scope_factory
        self._mapping_budget = mapping_budget or VariableMappingBudget(
            list_databases_limit=1,
            list_tables_limit=4,
            schema_reads_limit=10,
            max_total_calls=15,
        )
        self._pending_traces: list[object] = []

    def plan_probe_mapping(
        self,
        *,
        planner_input: MappingPlannerInput,
    ) -> VariableMappingPlanResult:
        self._pending_traces = []
        scoped_provider = self._scope_factory.create_mapping_provider(
            self._metadata_provider,
            self._mapping_budget,
        )
        try:
            planning_result = self._planner.plan(
                planner_input=planner_input,
                metadata_provider=scoped_provider,
            )
        except Exception as exc:
            self._pending_traces.extend(self._drain_scope_traces(scoped_provider))
            return VariableMappingPlanResult(
                failure_reason=f"变量映射失败：LLM 映射节点执行失败：{exc}",
                warnings=[f"变量映射节点异常：{exc}"],
            )
        self._pending_traces.extend(self._drain_scope_traces(scoped_provider))
        return planning_result

    def drain_tool_traces(self) -> list[object]:
        traces = list(self._pending_traces)
        self._pending_traces.clear()
        return traces

    def _drain_scope_traces(self, scoped_provider: object) -> list[object]:
        drain = getattr(scoped_provider, "drain_tool_traces", None)
        if not callable(drain):
            return []
        raw_traces = drain()
        if not isinstance(raw_traces, list):
            return []
        return cast(list[object], raw_traces)

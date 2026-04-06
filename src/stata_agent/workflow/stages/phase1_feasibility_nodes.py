from __future__ import annotations

from collections.abc import Sequence

from stata_agent.domains.fetch.types import ProbeCoverageResult, VariableProbeResult
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.workflow.observability import WorkflowNodeAudit, collect_trace_ids
from stata_agent.workflow.observability import drain_component_traces, merge_csmar_traces
from stata_agent.workflow.ports import DataContractBuilderPort, ProbeExecutorPort
from stata_agent.workflow.ports import RequirementParserPort, VariableMapperPort
from stata_agent.workflow.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.state_contracts import NodeAuditMap, Phase1StateUpdate
from stata_agent.workflow.types import RunStage


class Phase1FeasibilityNodes:
    def __init__(
        self,
        parser: RequirementParserPort,
        builder: VariableRequirementsBuilderPort,
        mapper: VariableMapperPort,
        probe_executor: ProbeExecutorPort,
        data_contract_builder: DataContractBuilderPort,
    ) -> None:
        self._parser = parser
        self._builder = builder
        self._mapper = mapper
        self._probe_executor = probe_executor
        self._data_contract_builder = data_contract_builder

    def parse_request(self, state: ResearchState) -> Phase1StateUpdate:
        result = self._parser.parse(state.request)
        notes = list(state.notes)
        if result.failure_reason is not None:
            notes.append(result.failure_reason)
            return {
                "parse_result": result,
                "stage": RunStage.FAILED,
                "notes": notes,
                "node_audits": self._with_node_audit(
                    state,
                    "parse_request",
                    input_summary={
                        "topic": state.request.topic,
                        "independent_variables_count": len(
                            state.request.independent_variables
                        ),
                    },
                    output_summary={"spec_ready": False},
                    warnings=list(result.warnings),
                    failure_reason=result.failure_reason,
                ),
            }

        assert result.spec is not None
        notes.append("需求解析已完成。")
        return {
            "spec": result.spec,
            "parse_result": result,
            "stage": RunStage.SPECIFIED,
            "notes": notes,
            "node_audits": self._with_node_audit(
                state,
                "parse_request",
                input_summary={
                    "topic": state.request.topic,
                    "independent_variables_count": len(
                        state.request.independent_variables
                    ),
                },
                output_summary={
                    "analysis_grain_candidates_count": len(
                        result.spec.analysis_grain_candidates
                    ),
                    "control_variable_candidates_count": len(
                        result.spec.control_variable_candidates
                    ),
                },
                warnings=list(result.warnings),
            ),
        }

    def build_variable_requirements(self, state: ResearchState) -> Phase1StateUpdate:
        if state.spec is None:
            return {}

        build_result = self._builder.build(state.spec)
        notes = list(state.notes)
        notes.append("变量定义与数据需求清单已生成。")
        return {
            "variable_definitions": build_result.variable_definitions,
            "data_requirements_draft": build_result.data_requirements_draft,
            "notes": notes,
            "node_audits": self._with_node_audit(
                state,
                "build_variable_requirements",
                input_summary={
                    "analysis_frequency_hint": state.spec.analysis_frequency_hint,
                    "analysis_grain_candidates_count": len(
                        state.spec.analysis_grain_candidates
                    ),
                },
                output_summary={
                    "variable_definitions_count": len(build_result.variable_definitions),
                    "data_requirement_items_count": len(
                        build_result.data_requirements_draft.items
                    ),
                },
                warnings=list(build_result.warnings),
            ),
        }

    def plan_probe_mapping(self, state: ResearchState) -> Phase1StateUpdate:
        if state.spec is None or state.variable_definitions is None:
            return {}

        planning_result = self._mapper.plan_probe_mapping(
            request=state.request,
            spec=state.spec,
            variable_definitions=state.variable_definitions,
        )
        mapping_traces = drain_component_traces(self._mapper)
        return {
            "mapping_plan_result": planning_result,
            "csmar_traces": merge_csmar_traces(state.csmar_traces, mapping_traces),
            "node_audits": self._with_node_audit(
                state,
                "plan_probe_mapping",
                input_summary={
                    "variable_definitions_count": len(state.variable_definitions),
                },
                output_summary={
                    "planned_items_count": len(planning_result.items),
                    "matched_items_count": sum(
                        1 for item in planning_result.items if item.matched
                    ),
                },
                warnings=list(planning_result.warnings),
                failure_reason=planning_result.failure_reason,
                trace_ids=collect_trace_ids(mapping_traces),
            ),
        }

    def materialize_variable_bindings(self, state: ResearchState) -> Phase1StateUpdate:
        if (
            state.spec is None
            or state.variable_definitions is None
            or state.mapping_plan_result is None
        ):
            return {}

        mapping_result = self._mapper.materialize_variable_bindings(
            request=state.request,
            spec=state.spec,
            variable_definitions=state.variable_definitions,
            planning_result=state.mapping_plan_result,
        )
        return self._mapping_updates(state, mapping_result)

    def run_field_probes(self, state: ResearchState) -> Phase1StateUpdate:
        if state.spec is None or state.variable_bindings is None:
            return {}

        probe_results = self._probe_executor.run_field_probes(
            spec=state.spec,
            variable_bindings=state.variable_bindings,
        )
        probe_traces = drain_component_traces(self._probe_executor)
        return {
            "probe_results_raw": probe_results,
            "csmar_traces": merge_csmar_traces(state.csmar_traces, probe_traces),
            "node_audits": self._with_node_audit(
                state,
                "run_field_probes",
                input_summary={"variable_bindings_count": len(state.variable_bindings)},
                output_summary={"probe_results_count": len(probe_results)},
                trace_ids=collect_trace_ids(probe_traces),
            ),
        }

    def summarize_probe_coverage(self, state: ResearchState) -> Phase1StateUpdate:
        if state.spec is None or state.probe_results_raw is None:
            return {}

        coverage_result = self._probe_executor.summarize_coverage(
            state.spec,
            state.probe_results_raw,
        )
        return self._probe_summary_updates(state, coverage_result)

    def build_data_contract(self, state: ResearchState) -> Phase1StateUpdate:
        if state.stage is RunStage.FAILED:
            return {}
        if (
            state.spec is None
            or state.variable_definitions is None
            or state.variable_bindings is None
            or state.probe_coverage_result is None
        ):
            return {}

        contract = self._data_contract_builder.build(
            request=state.request,
            spec=state.spec,
            variable_definitions=state.variable_definitions,
            variable_bindings=state.variable_bindings,
            probe_coverage=state.probe_coverage_result,
        )
        notes = list(state.notes)
        notes.append("最低可行数据契约已生成。")
        return {
            "data_contract_bundle": contract,
            "stage": RunStage.CONTRACTED,
            "notes": notes,
            "node_audits": self._with_node_audit(
                state,
                "build_data_contract",
                input_summary={
                    "variable_bindings_count": len(state.variable_bindings),
                    "hard_gaps_count": len(state.probe_coverage_result.hard_gaps),
                },
                output_summary={
                    "hard_contract_variables_count": len(contract.hard_contract_variables),
                    "soft_contract_variables_count": len(contract.soft_contract_variables),
                    "allowed_soft_removals_count": len(contract.allowed_soft_removals),
                },
                trace_ids=self._trace_ids_from_bindings(state.variable_bindings),
            ),
        }

    def _mapping_updates(
        self,
        state: ResearchState,
        mapping_result: VariableMappingResult,
    ) -> Phase1StateUpdate:
        notes = list(state.notes)
        notes.extend(mapping_result.warnings)
        trace_ids = self._trace_ids_from_bindings(mapping_result.bindings)
        updates: Phase1StateUpdate = {
            "variable_mapping_result": mapping_result,
            "node_audits": self._with_node_audit(
                state,
                "materialize_variable_bindings",
                input_summary={
                    "planned_items_count": len(state.mapping_plan_result.items)
                    if state.mapping_plan_result is not None
                    else 0,
                },
                output_summary={
                    "bindings_count": len(mapping_result.bindings),
                    "soft_contract_gaps_count": len(mapping_result.soft_contract_gaps),
                },
                warnings=list(mapping_result.warnings),
                failure_reason=mapping_result.failure_reason,
                trace_ids=trace_ids,
            ),
            "notes": notes,
        }
        if mapping_result.failure_reason is not None:
            notes.append(mapping_result.failure_reason)
            updates["stage"] = RunStage.FAILED
            return updates

        notes.append("CSMAR 探针级变量映射已完成。")
        resolved_definitions = mapping_result.resolved_variable_definitions
        if not resolved_definitions:
            assert state.variable_definitions is not None
            resolved_definitions = state.variable_definitions
        updates["variable_definitions"] = resolved_definitions
        updates["variable_bindings"] = mapping_result.bindings
        updates["stage"] = RunStage.MAPPED
        return updates

    def _probe_summary_updates(
        self,
        state: ResearchState,
        coverage_result: ProbeCoverageResult,
    ) -> Phase1StateUpdate:
        notes = list(state.notes)
        notes.extend(coverage_result.warnings)
        trace_ids = self._trace_ids_from_probe_results(coverage_result.probe_results)
        updates: Phase1StateUpdate = {
            "probe_coverage_result": coverage_result,
            "node_audits": self._with_node_audit(
                state,
                "summarize_probe_coverage",
                input_summary={"probe_results_count": len(state.probe_results_raw or [])},
                output_summary={
                    "hard_gaps_count": len(coverage_result.hard_gaps),
                    "soft_gaps_count": len(coverage_result.soft_gaps),
                    "hard_coverage_rate": coverage_result.hard_coverage_rate,
                    "soft_coverage_rate": coverage_result.soft_coverage_rate,
                },
                warnings=list(coverage_result.warnings),
                failure_reason=coverage_result.failure_reason,
                trace_ids=trace_ids,
            ),
            "notes": notes,
        }
        if coverage_result.failure_reason is not None:
            notes.append(coverage_result.failure_reason)
            updates["stage"] = RunStage.FAILED
            return updates

        notes.append("探针执行与覆盖摘要已完成。")
        updates["stage"] = RunStage.PROBED
        return updates

    def _with_node_audit(
        self,
        state: ResearchState,
        node_name: str,
        *,
        input_summary: dict[str, object],
        output_summary: dict[str, object],
        warnings: list[str] | None = None,
        failure_reason: str | None = None,
        trace_ids: list[str] | None = None,
    ) -> NodeAuditMap:
        audits = dict(state.node_audits)
        audits[node_name] = WorkflowNodeAudit(
            input_summary=input_summary,
            output_summary=output_summary,
            warnings=warnings or [],
            failure_reason=failure_reason,
            trace_ids=trace_ids or [],
        )
        return audits

    def _trace_ids_from_bindings(self, bindings: Sequence[object]) -> list[str]:
        trace_ids: list[str] = []
        for binding in bindings:
            trace_id = getattr(binding, "trace_id", "").strip()
            if trace_id and trace_id not in trace_ids:
                trace_ids.append(trace_id)
        return trace_ids

    def _trace_ids_from_probe_results(
        self,
        probe_results: list[VariableProbeResult],
    ) -> list[str]:
        trace_ids: list[str] = []
        for result in probe_results:
            trace_id = result.trace_id.strip()
            if trace_id and trace_id not in trace_ids:
                trace_ids.append(trace_id)
        return trace_ids

from typing import cast

from stata_agent.workflow.ports import DataContractBuilderPort
from stata_agent.workflow.ports import Phase1OrchestratorPort
from stata_agent.workflow.ports import ProbeExecutorPort
from stata_agent.workflow.ports import RequirementParserPort
from stata_agent.workflow.ports import VariableMapperPort
from stata_agent.workflow.ports import VariableRequirementsBuilderPort
from stata_agent.domains.mapping.types import CsmarToolTrace
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.types import RunStage


class Phase1FeasibilityOrchestrator(Phase1OrchestratorPort):
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

    def run_feasibility(self, state: ResearchState) -> ResearchState:
        state = self._parse_request_node(state)
        if state.stage is RunStage.FAILED:
            return state

        state = self._build_variable_requirements_node(state)
        state = self._map_variables_node(state)
        if state.stage is RunStage.FAILED:
            return state

        state = self._probe_coverage_node(state)
        if state.stage is RunStage.FAILED:
            return state

        return self._build_data_contract_node(state)

    def _parse_request_node(self, state: ResearchState) -> ResearchState:
        result = self._parser.parse(state.request)
        notes = list(state.notes)
        if result.failure_reason is not None:
            notes.append(result.failure_reason)
            return state.model_copy(
                update={
                    "parse_result": result,
                    "stage": RunStage.FAILED,
                    "notes": notes,
                }
            )

        notes.append("需求解析已完成。")
        return state.model_copy(
            update={
                "spec": result.spec,
                "parse_result": result,
                "stage": RunStage.SPECIFIED,
                "notes": notes,
            }
        )

    def _build_variable_requirements_node(self, state: ResearchState) -> ResearchState:
        if state.spec is None:
            return state

        build_result = self._builder.build(state.spec)
        notes = list(state.notes)
        notes.append("变量定义与数据需求清单已生成。")
        return state.model_copy(
            update={
                "variable_definitions": build_result.variable_definitions,
                "data_requirements_draft": build_result.data_requirements_draft,
                "notes": notes,
            }
        )

    def _map_variables_node(self, state: ResearchState) -> ResearchState:
        if state.spec is None or state.variable_definitions is None:
            return state

        mapping_result = self._mapper.map_probe_bindings(
            request=state.request,
            spec=state.spec,
            variable_definitions=state.variable_definitions,
        )
        mapping_traces = self._drain_component_traces(self._mapper)
        merged_traces = self._merge_traces(state.csmar_traces, mapping_traces)
        notes = list(state.notes)
        notes.extend(mapping_result.warnings)
        if mapping_result.failure_reason is not None:
            notes.append(mapping_result.failure_reason)
            return state.model_copy(
                update={
                    "variable_mapping_result": mapping_result,
                    "stage": RunStage.FAILED,
                    "csmar_traces": merged_traces,
                    "notes": notes,
                }
            )

        notes.append("CSMAR 探针级变量映射已完成。")
        return state.model_copy(
            update={
                "variable_mapping_result": mapping_result,
                "variable_definitions": mapping_result.resolved_variable_definitions
                or state.variable_definitions,
                "variable_bindings": mapping_result.bindings,
                "stage": RunStage.MAPPED,
                "csmar_traces": merged_traces,
                "notes": notes,
            }
        )

    def _probe_coverage_node(self, state: ResearchState) -> ResearchState:
        if state.spec is None or state.variable_bindings is None:
            return state

        coverage_result = self._probe_executor.execute_coverage(
            spec=state.spec,
            variable_bindings=state.variable_bindings,
        )
        probe_traces = self._drain_component_traces(self._probe_executor)
        merged_traces = self._merge_traces(state.csmar_traces, probe_traces)
        notes = list(state.notes)
        notes.extend(coverage_result.warnings)
        if coverage_result.failure_reason is not None:
            notes.append(coverage_result.failure_reason)
            return state.model_copy(
                update={
                    "probe_coverage_result": coverage_result,
                    "stage": RunStage.FAILED,
                    "csmar_traces": merged_traces,
                    "notes": notes,
                }
            )

        notes.append("探针执行与覆盖摘要已完成。")
        return state.model_copy(
            update={
                "probe_coverage_result": coverage_result,
                "stage": RunStage.PROBED,
                "csmar_traces": merged_traces,
                "notes": notes,
            }
        )

    def _build_data_contract_node(self, state: ResearchState) -> ResearchState:
        if state.stage is RunStage.FAILED:
            return state
        if (
            state.spec is None
            or state.variable_definitions is None
            or state.variable_bindings is None
            or state.probe_coverage_result is None
        ):
            return state

        contract = self._data_contract_builder.build(
            request=state.request,
            spec=state.spec,
            variable_definitions=state.variable_definitions,
            variable_bindings=state.variable_bindings,
            probe_coverage=state.probe_coverage_result,
        )
        notes = list(state.notes)
        notes.append("最低可行数据契约已生成。")
        return state.model_copy(
            update={
                "data_contract_bundle": contract,
                "stage": RunStage.CONTRACTED,
                "notes": notes,
            }
        )

    def _drain_component_traces(self, component: object) -> list[CsmarToolTrace]:
        drain = getattr(component, "drain_tool_traces", None)
        if not callable(drain):
            return []

        raw_traces_obj = drain()
        if not isinstance(raw_traces_obj, list):
            return []
        raw_traces = cast(list[object], raw_traces_obj)

        traces: list[CsmarToolTrace] = []
        for item in raw_traces:
            if isinstance(item, CsmarToolTrace):
                traces.append(item)
                continue
            try:
                traces.append(CsmarToolTrace.model_validate(item))
            except Exception:
                continue

        return traces

    def _merge_traces(
        self,
        existing: list[CsmarToolTrace],
        incoming: list[CsmarToolTrace],
    ) -> list[CsmarToolTrace]:
        merged_by_id: dict[str, CsmarToolTrace] = {}
        ordered_ids: list[str] = []
        for trace in [*existing, *incoming]:
            trace_id = trace.trace_id.strip()
            if not trace_id:
                continue
            if trace_id not in merged_by_id:
                merged_by_id[trace_id] = trace
                ordered_ids.append(trace_id)
                continue
            merged_by_id[trace_id] = self._merge_trace_pair(merged_by_id[trace_id], trace)

        return [merged_by_id[trace_id] for trace_id in ordered_ids]

    def _merge_trace_pair(
        self,
        current: CsmarToolTrace,
        incoming: CsmarToolTrace,
    ) -> CsmarToolTrace:
        current_score = self._trace_completeness_score(current)
        incoming_score = self._trace_completeness_score(incoming)
        if incoming_score > current_score:
            preferred, fallback = incoming, current
        elif incoming_score < current_score:
            preferred, fallback = current, incoming
        elif incoming.completed_at > current.completed_at:
            preferred, fallback = incoming, current
        else:
            preferred, fallback = current, incoming

        return preferred.model_copy(
            update={
                "request_payload": preferred.request_payload or fallback.request_payload,
                "result_summary": preferred.result_summary or fallback.result_summary,
                "error": preferred.error or fallback.error,
                "query_fingerprint": preferred.query_fingerprint or fallback.query_fingerprint,
                "validation_id": preferred.validation_id or fallback.validation_id,
                "cached": preferred.cached or fallback.cached,
            }
        )

    def _trace_completeness_score(self, trace: CsmarToolTrace) -> int:
        score = 0
        if trace.request_payload:
            score += 1
        if trace.result_summary:
            score += 2
        if trace.error:
            score += 2
        if trace.query_fingerprint:
            score += 1
        if trace.validation_id:
            score += 1
        if trace.cached:
            score += 1
        return score

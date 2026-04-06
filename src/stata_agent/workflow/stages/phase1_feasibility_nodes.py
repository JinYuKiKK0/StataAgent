from langchain_core.runnables.config import RunnableConfig

from stata_agent.services.audit.ports import AuditStorePort
from stata_agent.services.contract.ports import DataContractBuilderPort
from stata_agent.services.mapping.ports import ProbeMappingPlannerPort
from stata_agent.services.mapping.ports import VariableBindingMaterializerPort
from stata_agent.services.probe.ports import ProbeCoverageSummarizerPort
from stata_agent.services.probe.ports import ProbeExecutorPort
from stata_agent.services.spec.ports import RequirementParserPort
from stata_agent.services.spec.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.observability import collect_trace_ids
from stata_agent.workflow.observability import drain_component_traces
from stata_agent.workflow.state import Phase1Artifacts
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_audit import build_workflow_audit
from stata_agent.workflow.stages.phase1_selectors import (
    build_mapping_planner_input,
    build_probe_execution_input,
    load_mapping_plan_result,
    load_probe_results,
)
from stata_agent.workflow.stages.phase1_state_updates import (
    build_mapping_state_update,
    build_probe_summary_state_update,
)
from stata_agent.workflow.stages.phase1_threading import resolve_thread_id
from stata_agent.workflow.state_contracts import Phase1StateUpdate
from stata_agent.workflow.types import RunStage

class Phase1FeasibilityNodes:
    def __init__(
        self,
        parser: RequirementParserPort,
        builder: VariableRequirementsBuilderPort,
        mapping_planner: ProbeMappingPlannerPort,
        binding_materializer: VariableBindingMaterializerPort,
        probe_executor: ProbeExecutorPort,
        probe_summarizer: ProbeCoverageSummarizerPort,
        data_contract_builder: DataContractBuilderPort,
        audit_store: AuditStorePort,
        default_thread_id: str,
    ) -> None:
        self._parser = parser
        self._builder = builder
        self._mapping_planner = mapping_planner
        self._binding_materializer = binding_materializer
        self._probe_executor = probe_executor
        self._probe_summarizer = probe_summarizer
        self._data_contract_builder = data_contract_builder
        self._audit_store = audit_store
        self._default_thread_id = default_thread_id

    def parse_request(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> Phase1StateUpdate:
        result = self._parser.parse(state.request)
        thread_id = resolve_thread_id(config, self._default_thread_id)
        audit_ref = self._audit_store.write_audit(
            thread_id=thread_id,
            kind="parse_request",
            payload={
                "raw_response_text": result.raw_response_text or "",
                "parsing_error": result.parsing_error or "",
                "failure_reason": result.failure_reason or "",
                "warnings": list(result.warnings),
            },
        )
        notes = list(state.workflow_audit.notes)
        if result.failure_reason is not None:
            notes.append(result.failure_reason)
            return {
                "stage": RunStage.FAILED,
                "workflow_audit": build_workflow_audit(
                    state,
                    notes=notes,
                    node_name="parse_request",
                    input_summary={
                        "topic": state.request.topic,
                        "independent_variables_count": len(state.request.independent_variables),
                    },
                    output_summary={"spec_ready": False},
                    warnings=list(result.warnings),
                    failure_reason=result.failure_reason,
                    audit_refs=[audit_ref],
                ),
            }

        assert result.spec is not None
        notes.append("需求解析已完成。")
        return {
            "phase1_artifacts": state.phase1_artifacts.model_copy(
                update={"spec": result.spec}
            ),
            "stage": RunStage.SPECIFIED,
            "workflow_audit": build_workflow_audit(
                state,
                notes=notes,
                node_name="parse_request",
                input_summary={
                    "topic": state.request.topic,
                    "independent_variables_count": len(state.request.independent_variables),
                },
                output_summary={
                    "analysis_grain_candidates_count": len(result.spec.analysis_grain_candidates),
                    "control_variable_candidates_count": len(
                        result.spec.control_variable_candidates
                    ),
                },
                warnings=list(result.warnings),
                audit_refs=[audit_ref],
            ),
        }

    def build_variable_requirements(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> Phase1StateUpdate:
        spec = state.phase1_artifacts.spec
        if spec is None:
            return {}

        build_result = self._builder.build(spec)
        notes = list(state.workflow_audit.notes)
        notes.append("变量定义与数据需求清单已生成。")
        return {
            "phase1_artifacts": state.phase1_artifacts.model_copy(
                update={
                    "variable_definitions": build_result.variable_definitions,
                    "data_requirements_draft": build_result.data_requirements_draft,
                }
            ),
            "workflow_audit": build_workflow_audit(
                state,
                notes=notes,
                node_name="build_variable_requirements",
                input_summary={
                    "analysis_frequency_hint": spec.analysis_frequency_hint,
                    "analysis_grain_candidates_count": len(spec.analysis_grain_candidates),
                },
                output_summary={
                    "variable_definitions_count": len(build_result.variable_definitions),
                    "data_requirement_items_count": len(build_result.data_requirements_draft.items),
                },
                warnings=list(build_result.warnings),
            ),
        }

    def plan_probe_mapping(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> Phase1StateUpdate:
        planner_input = build_mapping_planner_input(state)
        if planner_input is None:
            return {}

        thread_id = resolve_thread_id(config, self._default_thread_id)
        planning_result = self._mapping_planner.plan_probe_mapping(
            planner_input=planner_input,
        )
        mapping_traces = drain_component_traces(self._mapping_planner)
        audit_ref = self._audit_store.write_audit(
            thread_id=thread_id,
            kind="plan_probe_mapping",
            payload={
                "planner_input": planner_input.model_dump(mode="json"),
                "planning_result": planning_result.model_dump(mode="json"),
            },
        )
        trace_refs = self._audit_store.write_traces(
            thread_id=thread_id,
            traces=[trace.model_dump(mode="json") for trace in mapping_traces],
        )
        return {
            "workflow_audit": build_workflow_audit(
                state,
                notes=list(state.workflow_audit.notes),
                node_name="plan_probe_mapping",
                input_summary={
                    "variable_definitions_count": len(planner_input.variable_definitions)
                },
                output_summary={
                    "planned_items_count": len(planning_result.items),
                    "matched_items_count": sum(1 for item in planning_result.items if item.matched),
                },
                warnings=list(planning_result.warnings),
                failure_reason=planning_result.failure_reason,
                audit_refs=[audit_ref],
                trace_refs=trace_refs or collect_trace_ids(mapping_traces),
            ),
        }

    def materialize_variable_bindings(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> Phase1StateUpdate:
        variable_definitions = state.phase1_artifacts.variable_definitions
        if variable_definitions is None:
            return {}

        thread_id = resolve_thread_id(config, self._default_thread_id)
        planning_result = load_mapping_plan_result(
            state=state,
            audit_store=self._audit_store,
            thread_id=thread_id,
        )
        if planning_result is None:
            return {}
        mapping_result = self._binding_materializer.materialize_variable_bindings(
            variable_definitions=variable_definitions,
            planning_result=planning_result,
        )
        audit_ref = self._audit_store.write_audit(
            thread_id=thread_id,
            kind="materialize_variable_bindings",
            payload={"mapping_result": mapping_result.model_dump(mode="json")},
        )
        return build_mapping_state_update(
            state,
            mapping_result,
            planned_items_count=len(planning_result.items),
            audit_refs=[audit_ref],
        )

    def run_field_probes(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> Phase1StateUpdate:
        probe_input = build_probe_execution_input(state)
        if probe_input is None:
            return {}

        thread_id = resolve_thread_id(config, self._default_thread_id)
        probe_results = self._probe_executor.run_field_probes(probe_input)
        probe_traces = drain_component_traces(self._probe_executor)
        audit_ref = self._audit_store.write_audit(
            thread_id=thread_id,
            kind="run_field_probes",
            payload={
                "probe_input": probe_input.model_dump(mode="json"),
                "probe_results": [item.model_dump(mode="json") for item in probe_results],
            },
        )
        trace_refs = self._audit_store.write_traces(
            thread_id=thread_id,
            traces=[trace.model_dump(mode="json") for trace in probe_traces],
        )
        return {
            "workflow_audit": build_workflow_audit(
                state,
                notes=list(state.workflow_audit.notes),
                node_name="run_field_probes",
                input_summary={
                    "variable_bindings_count": len(probe_input.variable_bindings)
                },
                output_summary={"probe_results_count": len(probe_results)},
                audit_refs=[audit_ref],
                trace_refs=trace_refs or collect_trace_ids(probe_traces),
            ),
        }

    def summarize_probe_coverage(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> Phase1StateUpdate:
        spec = state.phase1_artifacts.spec
        if spec is None:
            return {}

        thread_id = resolve_thread_id(config, self._default_thread_id)
        probe_results = load_probe_results(
            state=state,
            audit_store=self._audit_store,
            thread_id=thread_id,
        )
        if probe_results is None:
            return {}

        coverage_result = self._probe_summarizer.summarize_coverage(spec, probe_results)
        audit_ref = self._audit_store.write_audit(
            thread_id=thread_id,
            kind="summarize_probe_coverage",
            payload={"probe_coverage": coverage_result.model_dump(mode="json")},
        )
        return build_probe_summary_state_update(
            state,
            coverage_result,
            audit_refs=[audit_ref],
        )

    def build_data_contract(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> Phase1StateUpdate:
        if state.stage is RunStage.FAILED:
            return {}

        phase1 = state.phase1_artifacts
        if (
            phase1.spec is None
            or phase1.variable_definitions is None
            or phase1.variable_bindings is None
            or phase1.probe_coverage_result is None
        ):
            return {}

        contract = self._data_contract_builder.build(
            spec=phase1.spec,
            variable_definitions=phase1.variable_definitions,
            variable_bindings=phase1.variable_bindings,
            probe_coverage=phase1.probe_coverage_result,
        )
        thread_id = resolve_thread_id(config, self._default_thread_id)
        audit_ref = self._audit_store.write_audit(
            thread_id=thread_id,
            kind="build_data_contract",
            payload={"data_contract_bundle": contract.model_dump(mode="json")},
        )
        notes = list(state.workflow_audit.notes)
        notes.append("最低可行数据契约已生成。")
        return {
            "phase1_artifacts": Phase1Artifacts.model_validate(
                {"data_contract_bundle": contract}
            ),
            "stage": RunStage.CONTRACTED,
            "workflow_audit": build_workflow_audit(
                state,
                notes=notes,
                node_name="build_data_contract",
                input_summary={
                    "variable_bindings_count": len(phase1.variable_bindings),
                    "hard_gaps_count": len(phase1.probe_coverage_result.hard_gaps),
                },
                output_summary={
                    "hard_contract_variables_count": len(contract.hard_contract_variables),
                    "soft_contract_variables_count": len(contract.soft_contract_variables),
                    "allowed_soft_removals_count": len(contract.allowed_soft_removals),
                },
                audit_refs=[audit_ref],
            ),
        }

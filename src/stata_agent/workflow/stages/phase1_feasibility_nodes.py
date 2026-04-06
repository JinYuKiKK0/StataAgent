from __future__ import annotations

from stata_agent.services.contract.ports import DataContractBuilderPort
from stata_agent.services.mapping.ports import ProbeMappingPlannerPort
from stata_agent.services.mapping.ports import VariableBindingMaterializerPort
from stata_agent.services.probe.ports import ProbeCoverageSummarizerPort
from stata_agent.services.probe.ports import ProbeExecutorPort
from stata_agent.services.spec.ports import RequirementParserPort
from stata_agent.services.spec.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.observability import collect_trace_ids
from stata_agent.workflow.observability import drain_component_traces, merge_csmar_traces
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_audit import build_workflow_audit
from stata_agent.workflow.stages.phase1_audit import trace_ids_from_bindings
from stata_agent.workflow.stages.phase1_state_updates import build_mapping_state_update
from stata_agent.workflow.stages.phase1_state_updates import (
    build_probe_summary_state_update,
)
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
    ) -> None:
        self._parser = parser
        self._builder = builder
        self._mapping_planner = mapping_planner
        self._binding_materializer = binding_materializer
        self._probe_executor = probe_executor
        self._probe_summarizer = probe_summarizer
        self._data_contract_builder = data_contract_builder

    def parse_request(self, state: ResearchState) -> Phase1StateUpdate:
        result = self._parser.parse(state.request)
        notes = list(state.workflow_audit.notes)
        phase1 = state.phase1_artifacts.model_copy(update={"parse_result": result})
        if result.failure_reason is not None:
            notes.append(result.failure_reason)
            return {
                "phase1_artifacts": phase1,
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
                ),
            }

        assert result.spec is not None
        notes.append("需求解析已完成。")
        return {
            "phase1_artifacts": phase1.model_copy(update={"spec": result.spec}),
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
            ),
        }

    def build_variable_requirements(self, state: ResearchState) -> Phase1StateUpdate:
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

    def plan_probe_mapping(self, state: ResearchState) -> Phase1StateUpdate:
        spec = state.phase1_artifacts.spec
        variable_definitions = state.phase1_artifacts.variable_definitions
        if spec is None or variable_definitions is None:
            return {}

        planning_result = self._mapping_planner.plan_probe_mapping(
            request=state.request,
            spec=spec,
            variable_definitions=variable_definitions,
        )
        mapping_traces = drain_component_traces(self._mapping_planner)
        return {
            "phase1_artifacts": state.phase1_artifacts.model_copy(
                update={"mapping_plan_result": planning_result}
            ),
            "workflow_audit": build_workflow_audit(
                state,
                notes=list(state.workflow_audit.notes),
                node_name="plan_probe_mapping",
                csmar_traces=merge_csmar_traces(state.workflow_audit.csmar_traces, mapping_traces),
                input_summary={"variable_definitions_count": len(variable_definitions)},
                output_summary={
                    "planned_items_count": len(planning_result.items),
                    "matched_items_count": sum(1 for item in planning_result.items if item.matched),
                },
                warnings=list(planning_result.warnings),
                failure_reason=planning_result.failure_reason,
                trace_ids=collect_trace_ids(mapping_traces),
            ),
        }

    def materialize_variable_bindings(self, state: ResearchState) -> Phase1StateUpdate:
        spec = state.phase1_artifacts.spec
        variable_definitions = state.phase1_artifacts.variable_definitions
        planning_result = state.phase1_artifacts.mapping_plan_result
        if spec is None or variable_definitions is None or planning_result is None:
            return {}

        mapping_result = self._binding_materializer.materialize_variable_bindings(
            request=state.request,
            spec=spec,
            variable_definitions=variable_definitions,
            planning_result=planning_result,
        )
        return build_mapping_state_update(state, mapping_result)

    def run_field_probes(self, state: ResearchState) -> Phase1StateUpdate:
        spec = state.phase1_artifacts.spec
        variable_bindings = state.phase1_artifacts.variable_bindings
        if spec is None or variable_bindings is None:
            return {}

        probe_results = self._probe_executor.run_field_probes(
            spec=spec,
            variable_bindings=variable_bindings,
        )
        probe_traces = drain_component_traces(self._probe_executor)
        return {
            "phase1_artifacts": state.phase1_artifacts.model_copy(
                update={"probe_results_raw": probe_results}
            ),
            "workflow_audit": build_workflow_audit(
                state,
                notes=list(state.workflow_audit.notes),
                node_name="run_field_probes",
                csmar_traces=merge_csmar_traces(state.workflow_audit.csmar_traces, probe_traces),
                input_summary={"variable_bindings_count": len(variable_bindings)},
                output_summary={"probe_results_count": len(probe_results)},
                trace_ids=collect_trace_ids(probe_traces),
            ),
        }

    def summarize_probe_coverage(self, state: ResearchState) -> Phase1StateUpdate:
        spec = state.phase1_artifacts.spec
        probe_results = state.phase1_artifacts.probe_results_raw
        if spec is None or probe_results is None:
            return {}

        coverage_result = self._probe_summarizer.summarize_coverage(spec, probe_results)
        return build_probe_summary_state_update(state, coverage_result)

    def build_data_contract(self, state: ResearchState) -> Phase1StateUpdate:
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
            request=state.request,
            spec=phase1.spec,
            variable_definitions=phase1.variable_definitions,
            variable_bindings=phase1.variable_bindings,
            probe_coverage=phase1.probe_coverage_result,
        )
        notes = list(state.workflow_audit.notes)
        notes.append("最低可行数据契约已生成。")
        return {
            "phase1_artifacts": phase1.model_copy(update={"data_contract_bundle": contract}),
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
                trace_ids=trace_ids_from_bindings(phase1.variable_bindings),
            ),
        }

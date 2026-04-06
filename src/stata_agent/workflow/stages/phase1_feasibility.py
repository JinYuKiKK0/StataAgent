# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from __future__ import annotations

from typing import Literal, Protocol

from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import END, START, StateGraph

from stata_agent.services.contract.ports import DataContractBuilderPort
from stata_agent.services.mapping.ports import ProbeMappingPlannerPort
from stata_agent.services.mapping.ports import VariableBindingMaterializerPort
from stata_agent.services.probe.ports import ProbeCoverageSummarizerPort
from stata_agent.services.probe.ports import ProbeExecutorPort
from stata_agent.services.spec.ports import RequirementParserPort
from stata_agent.services.spec.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_feasibility_nodes import (
    Phase1FeasibilityNodes,
)
from stata_agent.workflow.types import RunStage


class Phase1OrchestratorPort(Protocol):
    def run_feasibility(
        self,
        state: ResearchState,
        *,
        config: RunnableConfig | None = None,
    ) -> ResearchState: ...


class Phase1FeasibilityOrchestrator(Phase1OrchestratorPort):
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
        self._nodes = Phase1FeasibilityNodes(
            parser=parser,
            builder=builder,
            mapping_planner=mapping_planner,
            binding_materializer=binding_materializer,
            probe_executor=probe_executor,
            probe_summarizer=probe_summarizer,
            data_contract_builder=data_contract_builder,
        )
        self._graph = self._build_graph()

    def run_feasibility(
        self,
        state: ResearchState,
        *,
        config: RunnableConfig | None = None,
    ) -> ResearchState:
        result = self._graph.invoke(state, config=config)
        if isinstance(result, ResearchState):
            return result
        return ResearchState.model_validate(result)

    def _build_graph(self):
        workflow = StateGraph(ResearchState)
        workflow.add_node("parse_request", self._nodes.parse_request)
        workflow.add_node(
            "build_variable_requirements",
            self._nodes.build_variable_requirements,
        )
        workflow.add_node("plan_probe_mapping", self._nodes.plan_probe_mapping)
        workflow.add_node(
            "materialize_variable_bindings",
            self._nodes.materialize_variable_bindings,
        )
        workflow.add_node("run_field_probes", self._nodes.run_field_probes)
        workflow.add_node(
            "summarize_probe_coverage",
            self._nodes.summarize_probe_coverage,
        )
        workflow.add_node("build_data_contract", self._nodes.build_data_contract)

        workflow.add_edge(START, "parse_request")
        workflow.add_conditional_edges(
            "parse_request",
            self._route_after_parse_request,
            ["build_variable_requirements", "__end__"],
        )
        workflow.add_edge("build_variable_requirements", "plan_probe_mapping")
        workflow.add_edge("plan_probe_mapping", "materialize_variable_bindings")
        workflow.add_conditional_edges(
            "materialize_variable_bindings",
            self._route_after_materialization,
            ["run_field_probes", "__end__"],
        )
        workflow.add_edge("run_field_probes", "summarize_probe_coverage")
        workflow.add_conditional_edges(
            "summarize_probe_coverage",
            self._route_after_probe_summary,
            ["build_data_contract", "__end__"],
        )
        workflow.add_edge("build_data_contract", END)
        return workflow.compile()

    def _route_after_parse_request(
        self,
        state: ResearchState,
    ) -> Literal["build_variable_requirements", "__end__"]:
        if state.stage is RunStage.FAILED:
            return "__end__"
        return "build_variable_requirements"

    def _route_after_materialization(
        self,
        state: ResearchState,
    ) -> Literal["run_field_probes", "__end__"]:
        if state.stage is RunStage.FAILED:
            return "__end__"
        return "run_field_probes"

    def _route_after_probe_summary(
        self,
        state: ResearchState,
    ) -> Literal["build_data_contract", "__end__"]:
        if state.stage is RunStage.FAILED:
            return "__end__"
        return "build_data_contract"

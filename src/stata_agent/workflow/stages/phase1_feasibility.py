# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from __future__ import annotations

from typing import Literal

from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import END, START, StateGraph

from stata_agent.workflow.ports import DataContractBuilderPort
from stata_agent.workflow.ports import Phase1OrchestratorPort
from stata_agent.workflow.ports import ProbeExecutorPort
from stata_agent.workflow.ports import RequirementParserPort
from stata_agent.workflow.ports import VariableMapperPort
from stata_agent.workflow.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_feasibility_nodes import (
    Phase1FeasibilityNodes,
)
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
        self._nodes = Phase1FeasibilityNodes(
            parser=parser,
            builder=builder,
            mapper=mapper,
            probe_executor=probe_executor,
            data_contract_builder=data_contract_builder,
        )
        self._graph = self._build_graph()

    @property
    def compiled_graph(self):
        return self._graph

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

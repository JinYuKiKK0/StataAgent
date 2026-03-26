# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from collections.abc import Callable
from typing import Any, Literal, cast
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt, Command
from langchain_core.runnables.config import RunnableConfig

from stata_agent.domains.fetch.types import GatewayDecision, GatewayRecord
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.providers.llm import TongyiResearchSpecGenerator
from stata_agent.providers.settings import Settings, SettingsError, get_settings
from stata_agent.services.data_contract_builder import DataContractBuilder
from stata_agent.services.probe_executor import ProbeExecutor
from stata_agent.services.requirement_parser import RequirementParser
from stata_agent.services.variable_mapper import VariableMapper
from stata_agent.services.variable_requirements_builder import (
    VariableRequirementsBuilder,
)
from stata_agent.workflow.ports import CsmarMetadataProviderPort
from stata_agent.workflow.ports import DataContractBuilderPort
from stata_agent.workflow.ports import Phase1OrchestratorPort
from stata_agent.workflow.ports import ProbeExecutorPort
from stata_agent.workflow.ports import RequirementParserPort
from stata_agent.workflow.ports import VariableMapperPort
from stata_agent.workflow.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator
from stata_agent.workflow.types import RunStage


class WorkflowBootstrapError(RuntimeError):
    def __init__(self, details: list[str]) -> None:
        super().__init__("工作流启动配置校验失败")
        self.details = details


class ApplicationOrchestrator:
    def __init__(
        self,
        parser: RequirementParserPort | None = None,
        builder: VariableRequirementsBuilderPort | None = None,
        mapper: VariableMapperPort | None = None,
        probe_executor: ProbeExecutorPort | None = None,
        data_contract_builder: DataContractBuilderPort | None = None,
        csmar_provider: CsmarMetadataProviderPort | None = None,
        phase1_orchestrator: Phase1OrchestratorPort | None = None,
        settings_factory: Callable[[], Settings] = get_settings,
    ) -> None:
        self._settings_factory = settings_factory
        self._parser = parser
        self._builder = builder
        self._mapper = mapper
        self._probe_executor = probe_executor
        self._data_contract_builder = data_contract_builder
        self._csmar_provider = csmar_provider
        self._phase1_orchestrator = phase1_orchestrator
        self._settings: Settings | None = None
        self._checkpointer = InMemorySaver()
        self._graph = self._build_graph()

    def create_initial_state(self, request: ResearchRequest) -> ResearchState:
        return ResearchState(request=request)

    def run(self, request: ResearchRequest) -> tuple[ResearchState, str]:
        """启动工作流。返回 (state, thread_id)。

        如果工作流命中 Gateway 中断，返回的 state.stage 为 CONTRACTED，
        调用方应使用 thread_id 调用 resume() 提交决策。
        """
        thread_id = f"run-{uuid4()}"
        initial_state = self.create_initial_state(request)
        result = self._graph.invoke(
            initial_state, config=self._build_run_config(thread_id)
        )
        return self._extract_state(result), thread_id

    def resume(self, thread_id: str, decision: dict[str, str]) -> ResearchState:
        """用人类决策恢复被中断的工作流。

        decision 格式: {"decision": "approved"|"rejected", "reason": "..."}
        """
        config = self._build_run_config(thread_id)
        result = self._graph.invoke(Command(resume=decision), config)
        return self._extract_state(result)

    def app_name(self) -> str:
        return self._load_settings().app_name

    # ── Graph topology ──

    def _build_graph(self):
        workflow = StateGraph(ResearchState)
        workflow.add_node("phase1_feasibility", self._run_phase1_node)
        workflow.add_node("gateway_approval", self._gateway_approval_node)

        workflow.add_edge(START, "phase1_feasibility")
        workflow.add_conditional_edges(
            "phase1_feasibility",
            self._route_after_phase1,
            ["gateway_approval", "__end__"],
        )
        workflow.add_edge("gateway_approval", END)

        return workflow.compile(checkpointer=self._checkpointer)

    # ── Graph nodes ──

    def _run_phase1_node(self, state: ResearchState) -> ResearchState:
        return self._get_phase1_orchestrator().run_feasibility(state)

    def _gateway_approval_node(self, state: ResearchState) -> dict[str, Any]:
        """Gateway 审批中断与恢复。

        interrupt() 前无副作用 → 幂等安全。
        """
        contract = state.data_contract_bundle
        approval_payload = {
            "action": "gateway_approval",
            "message": "请审核最低可行数据契约并决定是否批准",
            "hard_contract_variables": contract.hard_contract_variables
            if contract
            else [],
            "soft_contract_variables": contract.soft_contract_variables
            if contract
            else [],
            "allowed_soft_removals": contract.allowed_soft_removals if contract else [],
            "residual_risks": contract.residual_risks if contract else [],
            "analysis_grain": contract.analysis_grain if contract else "",
            "entity_scope": contract.entity_scope if contract else "",
            "time_range": f"{contract.time_start_year}-{contract.time_end_year}"
            if contract
            else "",
        }

        # ── interrupt: 暂停等待人类决策 ──
        human_decision = interrupt(approval_payload)

        # ── resume: 处理人类决策 ──
        decision_data = (
            cast(dict[str, str], human_decision)
            if isinstance(human_decision, dict)
            else {}
        )
        decision_str: str = str(decision_data.get("decision", "rejected"))
        reason: str = str(decision_data.get("reason", ""))

        notes = list(state.notes)
        if decision_str == "approved":
            record = GatewayRecord(decision=GatewayDecision.APPROVED, reason=reason)
            notes.append("Gateway 审批通过，数据契约已锁定。")
            return {
                "gateway_record": record,
                "stage": RunStage.APPROVED,
                "notes": notes,
            }
        else:
            record = GatewayRecord(decision=GatewayDecision.REJECTED, reason=reason)
            notes.append(f"Gateway 审批被驳回：{reason}")
            return {
                "gateway_record": record,
                "stage": RunStage.FAILED,
                "notes": notes,
            }

    # ── Routing ──

    def _route_after_phase1(
        self, state: ResearchState
    ) -> Literal["gateway_approval", "__end__"]:
        if state.stage is RunStage.CONTRACTED:
            return "gateway_approval"
        return "__end__"

    # ── Config ──

    def _build_run_config(self, thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}}

    def _extract_state(self, result: object) -> ResearchState:
        if isinstance(result, ResearchState):
            return result
        return ResearchState.model_validate(result)

    # ── Dependency resolution ──

    def _get_parser(self) -> RequirementParserPort:
        if self._parser is None:
            generator = TongyiResearchSpecGenerator(self._load_settings())
            self._parser = RequirementParser(generator=generator)
        return self._parser

    def _get_builder(self) -> VariableRequirementsBuilderPort:
        if self._builder is None:
            self._builder = VariableRequirementsBuilder()
        return self._builder

    def _get_mapper(self) -> VariableMapperPort:
        if self._mapper is None:
            self._mapper = VariableMapper(metadata_provider=self._get_csmar_provider())
        return self._mapper

    def _get_probe_executor(self) -> ProbeExecutorPort:
        if self._probe_executor is None:
            self._probe_executor = ProbeExecutor(
                metadata_provider=self._get_csmar_provider()
            )
        return self._probe_executor

    def _get_data_contract_builder(self) -> DataContractBuilderPort:
        if self._data_contract_builder is None:
            self._data_contract_builder = DataContractBuilder()
        return self._data_contract_builder

    def _get_phase1_orchestrator(self) -> Phase1OrchestratorPort:
        if self._phase1_orchestrator is None:
            self._phase1_orchestrator = Phase1FeasibilityOrchestrator(
                parser=self._get_parser(),
                builder=self._get_builder(),
                mapper=self._get_mapper(),
                probe_executor=self._get_probe_executor(),
                data_contract_builder=self._get_data_contract_builder(),
            )
        return self._phase1_orchestrator

    def _get_csmar_provider(self) -> CsmarMetadataProviderPort:
        if self._csmar_provider is None:
            self._csmar_provider = CsmarBridgeClient()
        return self._csmar_provider

    def _load_settings(self) -> Settings:
        if self._settings is None:
            try:
                self._settings = self._settings_factory()
            except SettingsError as exc:
                raise WorkflowBootstrapError(exc.details) from exc
        return self._settings

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from collections.abc import Callable
from uuid import uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.runnables.config import RunnableConfig

from stata_agent.domains.fetch.types import GatewayResumeRequest
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.providers.llm import TongyiResearchSpecGenerator
from stata_agent.providers.llm import TongyiVariableSemanticJudge
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
from stata_agent.workflow.graph import build_workflow_graph
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator


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
        checkpointer_factory: Callable[[], BaseCheckpointSaver[str]] | None = InMemorySaver,
    ) -> None:
        self._settings_factory = settings_factory
        self._parser = parser
        self._builder = builder
        self._mapper = mapper
        self._probe_executor = probe_executor
        self._data_contract_builder = data_contract_builder
        self._csmar_provider = csmar_provider
        self._phase1_orchestrator = phase1_orchestrator
        self._semantic_judge: TongyiVariableSemanticJudge | None = None
        self._settings: Settings | None = None
        self._checkpointer = (
            checkpointer_factory() if checkpointer_factory is not None else None
        )
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

    def resume(self, thread_id: str, decision: GatewayResumeRequest) -> ResearchState:
        """用人类决策恢复被中断的工作流。

        decision 格式: GatewayResumeRequest(decision=approved|rejected, reason="...")
        """
        config = self._build_run_config(thread_id)
        result = self._graph.invoke(Command(resume=decision.model_dump(mode="json")), config)
        return self._extract_state(result)

    def app_name(self) -> str:
        return self._load_settings().app_name

    # ── Graph topology ──

    def _build_graph(self):
        return build_workflow_graph(
            self._run_phase1_node,
            checkpointer=self._checkpointer,
        )

    # ── Graph nodes ──

    def _run_phase1_node(self, state: ResearchState) -> ResearchState:
        return self._get_phase1_orchestrator().run_feasibility(state)

    # ── Config ──

    def _build_run_config(self, thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}}

    def _extract_state(self, result: object) -> ResearchState:
        if isinstance(result, ResearchState):
            return result
        return ResearchState.model_validate(result)

    @property
    def compiled_graph(self):
        return self._graph

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
            self._mapper = VariableMapper(
                metadata_provider=self._get_csmar_provider(),
                semantic_judge=self._get_semantic_judge(),
            )
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

    def _get_semantic_judge(self) -> TongyiVariableSemanticJudge:
        if self._semantic_judge is None:
            self._semantic_judge = TongyiVariableSemanticJudge(self._load_settings())
        return self._semantic_judge

    def _get_csmar_provider(self) -> CsmarMetadataProviderPort:
        if self._csmar_provider is None:
            settings = self._load_settings()
            password = (
                settings.csmar_password.get_secret_value()
                if settings.csmar_password is not None
                else None
            )
            self._csmar_provider = CsmarBridgeClient(
                account=settings.csmar_account,
                password=password,
                language=settings.csmar_language,
            )
        return self._csmar_provider

    def _load_settings(self) -> Settings:
        if self._settings is None:
            try:
                self._settings = self._settings_factory()
            except SettingsError as exc:
                raise WorkflowBootstrapError(exc.details) from exc
        return self._settings

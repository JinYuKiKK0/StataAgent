# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from collections.abc import Callable
from uuid import uuid4

from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.settings import Settings
from stata_agent.providers.settings import SettingsError
from stata_agent.providers.settings import get_settings
from stata_agent.services.contract.ports import DataContractBuilderPort
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.mapping.ports import ProbeMappingPlannerPort
from stata_agent.services.mapping.ports import VariableBindingMaterializerPort
from stata_agent.services.probe.ports import ProbeCoverageSummarizerPort
from stata_agent.services.probe.ports import ProbeExecutorPort
from stata_agent.services.spec.ports import RequirementParserPort
from stata_agent.services.spec.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.bootstrap import build_application_dependencies
from stata_agent.workflow.gateway import GatewayResumeRequest
from stata_agent.workflow.graph import build_workflow_graph
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.stages.phase1_feasibility import Phase1OrchestratorPort


class WorkflowBootstrapError(RuntimeError):
    def __init__(self, details: list[str]) -> None:
        super().__init__("工作流启动配置校验失败")
        self.details = details


class ApplicationOrchestrator:
    def __init__(
        self,
        parser: RequirementParserPort | None = None,
        builder: VariableRequirementsBuilderPort | None = None,
        mapping_planner: ProbeMappingPlannerPort | None = None,
        binding_materializer: VariableBindingMaterializerPort | None = None,
        probe_executor: ProbeExecutorPort | None = None,
        probe_summarizer: ProbeCoverageSummarizerPort | None = None,
        data_contract_builder: DataContractBuilderPort | None = None,
        csmar_provider: CsmarMetadataProviderPort | None = None,
        phase1_orchestrator: Phase1OrchestratorPort | None = None,
        settings_factory: Callable[[], Settings] = get_settings,
        checkpointer_factory: Callable[[], BaseCheckpointSaver[str]] | None = InMemorySaver,
    ) -> None:
        try:
            self._dependencies = build_application_dependencies(
                parser=parser,
                builder=builder,
                mapping_planner=mapping_planner,
                binding_materializer=binding_materializer,
                probe_executor=probe_executor,
                probe_summarizer=probe_summarizer,
                data_contract_builder=data_contract_builder,
                csmar_provider=csmar_provider,
                phase1_orchestrator=phase1_orchestrator,
                settings_factory=settings_factory,
            )
        except SettingsError as exc:
            raise WorkflowBootstrapError(exc.details) from exc
        self._checkpointer = (
            checkpointer_factory() if checkpointer_factory is not None else None
        )
        self._graph = self._build_graph()

    def create_initial_state(self, request: ResearchRequest) -> ResearchState:
        return ResearchState(request=request)

    def run(self, request: ResearchRequest) -> tuple[ResearchState, str]:
        thread_id = f"run-{uuid4()}"
        initial_state = self.create_initial_state(request)
        result = self._graph.invoke(
            initial_state, config=self._build_run_config(thread_id)
        )
        return self._extract_state(result), thread_id

    def resume(self, thread_id: str, decision: GatewayResumeRequest) -> ResearchState:
        config = self._build_run_config(thread_id)
        result = self._graph.invoke(Command(resume=decision.model_dump(mode="json")), config)
        return self._extract_state(result)

    def app_name(self) -> str:
        return self._dependencies.settings.app_name

    def _build_graph(self):
        return build_workflow_graph(
            self._run_phase1_node,
            checkpointer=self._checkpointer,
        )

    def _run_phase1_node(
        self,
        state: ResearchState,
        config: RunnableConfig | None = None,
    ) -> ResearchState:
        return self._dependencies.phase1_orchestrator.run_feasibility(
            state, config=config
        )

    def _build_run_config(self, thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}}

    def _extract_state(self, result: object) -> ResearchState:
        if isinstance(result, ResearchState):
            return result
        return ResearchState.model_validate(result)

    @property
    def compiled_graph(self):
        return self._graph

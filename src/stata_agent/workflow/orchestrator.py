# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from collections.abc import Callable
from typing import Protocol

from langgraph.graph import END, START, StateGraph

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableRequirementsResult
from stata_agent.providers.llm import TongyiResearchSpecGenerator
from stata_agent.providers.settings import Settings, SettingsError, get_settings
from stata_agent.services.requirement_parser import RequirementParser
from stata_agent.services.variable_requirements_builder import VariableRequirementsBuilder
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.types import RunStage


class RequirementParserPort(Protocol):
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        ...


class VariableRequirementsBuilderPort(Protocol):
    def build(self, spec: ResearchSpec) -> VariableRequirementsResult:
        ...


class WorkflowBootstrapError(RuntimeError):
    def __init__(self, details: list[str]) -> None:
        super().__init__("工作流启动配置校验失败")
        self.details = details


class ApplicationOrchestrator:
    def __init__(
        self,
        parser: RequirementParserPort | None = None,
        builder: VariableRequirementsBuilderPort | None = None,
        settings_factory: Callable[[], Settings] = get_settings,
    ) -> None:
        self._settings_factory = settings_factory
        self._parser = parser
        self._builder = builder
        self._settings: Settings | None = None
        self._graph = self._build_graph()

    def create_initial_state(self, request: ResearchRequest) -> ResearchState:
        """创建初始研究状态，包含请求和初始阶段标记。"""
        return ResearchState(request=request)

    def run(self, request: ResearchRequest) -> ResearchState:
        initial_state = self.create_initial_state(request)
        result = self._graph.invoke(initial_state)
        if isinstance(result, ResearchState):
            return result
        return ResearchState.model_validate(result)

    def app_name(self) -> str:
        return self._load_settings().app_name

    def _build_graph(self):
        workflow = StateGraph(ResearchState)
        workflow.add_node("parse_request", self._parse_request_node)
        workflow.add_node("build_variable_requirements", self._build_variable_requirements_node)
        workflow.add_edge(START, "parse_request")
        workflow.add_edge("parse_request", "build_variable_requirements")
        workflow.add_edge("build_variable_requirements", END)
        return workflow.compile()

    def _parse_request_node(self, state: ResearchState) -> ResearchState:
        result = self._get_parser().parse(state.request)
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

        build_result = self._get_builder().build(state.spec)
        notes = list(state.notes)
        notes.append("变量定义与数据需求清单已生成。")
        return state.model_copy(
            update={
                "variable_definitions": build_result.variable_definitions,
                "data_requirements_draft": build_result.data_requirements_draft,
                "notes": notes,
            }
        )

    def _get_parser(self) -> RequirementParserPort:
        if self._parser is None:
            generator = TongyiResearchSpecGenerator(self._load_settings())
            self._parser = RequirementParser(generator=generator)
        return self._parser

    def _get_builder(self) -> VariableRequirementsBuilderPort:
        if self._builder is None:
            self._builder = VariableRequirementsBuilder()
        return self._builder

    def _load_settings(self) -> Settings:
        if self._settings is None:
            try:
                self._settings = self._settings_factory()
            except SettingsError as exc:
                raise WorkflowBootstrapError(exc.details) from exc
        return self._settings

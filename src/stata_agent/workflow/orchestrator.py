# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from collections.abc import Callable
from typing import Protocol

from langgraph.graph import END, START, StateGraph

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.providers.llm import TongyiResearchSpecGenerator
from stata_agent.providers.settings import Settings, get_settings
from stata_agent.services.requirement_parser import RequirementParser
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.types import RunStage


class RequirementParserPort(Protocol):
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        ...


class ApplicationOrchestrator:
    def __init__(
        self,
        parser: RequirementParserPort | None = None,
        settings_factory: Callable[[], Settings] = get_settings,
    ) -> None:
        self._settings_factory = settings_factory
        self._parser = parser
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

    def _build_graph(self):
        workflow = StateGraph(ResearchState)
        workflow.add_node("parse_request", self._parse_request_node)
        workflow.add_edge(START, "parse_request")
        workflow.add_edge("parse_request", END)
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

    def _get_parser(self) -> RequirementParserPort:
        if self._parser is None:
            generator = TongyiResearchSpecGenerator(self._settings_factory())
            self._parser = RequirementParser(generator=generator)
        return self._parser

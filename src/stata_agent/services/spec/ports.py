from typing import Protocol

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.spec.contracts import RequirementParseResult
from stata_agent.services.spec.contracts import VariableRequirementsResult


class ResearchSpecGenerator(Protocol):
    def parse_request(self, request: ResearchRequest) -> RequirementParseResult:
        """从研究请求生成带审计信息的结构化规范。"""
        ...


class RequirementParserPort(Protocol):
    def parse(self, request: ResearchRequest) -> RequirementParseResult: ...


class VariableRequirementsBuilderPort(Protocol):
    def build(self, spec: ResearchSpec) -> VariableRequirementsResult: ...

from typing import Protocol

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult


class ResearchSpecGenerator(Protocol):
    def parse_request(self, request: ResearchRequest) -> RequirementParseResult:
        """从研究请求生成带审计信息的结构化规范。"""
        ...

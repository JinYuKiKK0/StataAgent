from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec


class RequirementParser:
    def parse(self, request: ResearchRequest) -> ResearchSpec:
        return ResearchSpec(
            topic=request.topic,
            dependent_variable=request.dependent_variable,
            independent_variables=request.independent_variables,
            controls=[],
            analysis_grain="unspecified",
        )


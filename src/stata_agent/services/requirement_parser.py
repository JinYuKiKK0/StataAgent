from stata_agent.domain.models import ResearchRequest, ResearchSpec


class RequirementParser:
    def parse(self, request: ResearchRequest) -> ResearchSpec:
        return ResearchSpec(topic=request.topic)


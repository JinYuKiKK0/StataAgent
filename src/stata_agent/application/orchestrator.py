from stata_agent.domain.models import ResearchRequest
from stata_agent.workflows.states import ResearchState


class ApplicationOrchestrator:
    def create_initial_state(self, request: ResearchRequest) -> ResearchState:
        return ResearchState(request=request)


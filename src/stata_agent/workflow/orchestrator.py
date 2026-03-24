from stata_agent.domains.request.types import ResearchRequest
from stata_agent.workflow.state import ResearchState


class ApplicationOrchestrator:
    def create_initial_state(self, request: ResearchRequest) -> ResearchState:
        """创建初始研究状态，包含请求和初始阶段标记。"""
        return ResearchState(request=request)

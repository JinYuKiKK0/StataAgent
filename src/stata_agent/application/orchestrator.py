from pydantic import ValidationError

from stata_agent.domain.models import ResearchRequest, ResearchSpec
from stata_agent.workflows.states import ResearchState


class ApplicationOrchestrator:
    def create_initial_state(self, request: ResearchRequest) -> ResearchState:
        """创建初始研究状态，包含请求和初始阶段标记。

        Args:
            request: 已验证的研究请求对象

        Returns:
            ResearchState: 初始工作流状态

        Raises:
            ValidationError: 如果请求校验失败（Pydantic 已在模型层面处理）
        """
        return ResearchState(request=request)


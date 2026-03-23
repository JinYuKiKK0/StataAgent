from stata_agent.domain.enums import RunStage


class ResultJudge:
    def final_stage(self, passed: bool) -> RunStage:
        return RunStage.COMPLETED if passed else RunStage.FAILED


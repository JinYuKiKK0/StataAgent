from typing import Literal


class ResultJudge:
    def final_stage(self, passed: bool) -> Literal["completed", "failed"]:
        return "completed" if passed else "failed"

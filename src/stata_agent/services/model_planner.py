from stata_agent.domain.models import ResearchSpec


class ModelPlanner:
    def build_baseline_formula(self, spec: ResearchSpec) -> str:
        dependent = spec.dependent_variable or "y"
        independent = spec.independent_variables[0] if spec.independent_variables else "x"
        return f"{dependent} = beta * {independent} + controls + fe + error"


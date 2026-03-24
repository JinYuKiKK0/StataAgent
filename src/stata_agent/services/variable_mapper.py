from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec


class VariableMapper:
    def map_core_variables(self, spec: ResearchSpec) -> list[VariableBinding]:
        if not spec.independent_variables:
            return []

        return [
            VariableBinding(
                variable_name=variable,
                table_name="UNMAPPED",
                field_name="UNMAPPED",
                confidence=0.0,
            )
            for variable in spec.independent_variables
        ]

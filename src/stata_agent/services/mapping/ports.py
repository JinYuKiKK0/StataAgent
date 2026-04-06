from collections.abc import Sequence
from typing import Protocol

from stata_agent.services.mapping.contracts import CsmarFieldProbeRequest
from stata_agent.services.mapping.contracts import CsmarFieldProbeResult
from stata_agent.services.mapping.contracts import CsmarTableRecord
from stata_agent.services.mapping.contracts import CsmarTableSchema
from stata_agent.services.mapping.contracts import MappingPlannerInput
from stata_agent.services.mapping.contracts import VariableMappingBudget
from stata_agent.services.mapping.contracts import VariableMappingPlanResult
from stata_agent.services.mapping.contracts import VariableMappingResult
from stata_agent.domains.spec.types import VariableDefinition


class CsmarMetadataProviderPort(Protocol):
    def list_databases(self) -> list[str]: ...

    def list_tables(self, database_name: str) -> list[CsmarTableRecord]: ...

    def get_table_schema(self, table_code: str) -> CsmarTableSchema: ...

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult: ...


class ScopedMetadataProviderPort(CsmarMetadataProviderPort, Protocol):
    def drain_tool_traces(self) -> Sequence[object]: ...


class MappingProviderScopePort(Protocol):
    def create_mapping_provider(
        self,
        metadata_provider: CsmarMetadataProviderPort,
        budget: VariableMappingBudget,
    ) -> ScopedMetadataProviderPort: ...


class MappingPlannerPort(Protocol):
    def plan(
        self,
        *,
        planner_input: MappingPlannerInput,
        metadata_provider: CsmarMetadataProviderPort,
    ) -> VariableMappingPlanResult: ...


class ProbeMappingPlannerPort(Protocol):
    def plan_probe_mapping(
        self,
        *,
        planner_input: MappingPlannerInput,
    ) -> VariableMappingPlanResult: ...

    def drain_tool_traces(self) -> Sequence[object]: ...


class VariableBindingMaterializerPort(Protocol):
    def materialize_variable_bindings(
        self,
        *,
        variable_definitions: list[VariableDefinition],
        planning_result: VariableMappingPlanResult,
    ) -> VariableMappingResult: ...

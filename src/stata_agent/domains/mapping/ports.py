from typing import Protocol

from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarTableRecord
from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import VariableMappingPlanResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition


class CsmarMetadataProviderPort(Protocol):
    def list_databases(self) -> list[str]: ...

    def list_tables(self, database_name: str) -> list[CsmarTableRecord]: ...

    def get_table_schema(self, table_code: str) -> CsmarTableSchema: ...

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult: ...


class VariableMappingPlannerPort(Protocol):
    def plan(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        metadata_provider: CsmarMetadataProviderPort,
    ) -> VariableMappingPlanResult: ...

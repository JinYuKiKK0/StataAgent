from typing import Protocol

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import CsmarFieldSearchHit
from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest
from stata_agent.domains.mapping.types import CsmarTableCandidate
from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import CsmarTableSearchRequest
from stata_agent.domains.mapping.types import VariableMatchDecision
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition


class CsmarMetadataProviderPort(Protocol):
    def search_tables(
        self, request: CsmarTableSearchRequest
    ) -> list[CsmarTableCandidate]: ...

    def get_table_schema(self, table_code: str) -> CsmarTableSchema: ...

    def search_fields(
        self, request: CsmarFieldSearchRequest
    ) -> list[CsmarFieldSearchHit]: ...

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult: ...


class VariableSemanticJudgePort(Protocol):
    def judge(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        definition: VariableDefinition,
        candidates: list[CsmarFieldCandidate],
    ) -> VariableMatchDecision: ...

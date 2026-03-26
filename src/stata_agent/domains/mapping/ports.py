from typing import Protocol

from stata_agent.domains.mapping.types import CsmarFieldCandidate


class CsmarMetadataProviderPort(Protocol):
    def find_field_candidates(self, variable_name: str) -> list[CsmarFieldCandidate]:
        ...

    def field_exists(self, table_name: str, field_name: str) -> bool:
        ...

    def query_count(self, table_name: str, field_name: str) -> int:
        ...

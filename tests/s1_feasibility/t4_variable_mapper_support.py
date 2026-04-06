"""S1-T4 变量映射测试支撑组件。"""

from __future__ import annotations

from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarFieldSearchHit
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest
from stata_agent.domains.mapping.types import CsmarSchemaField
from stata_agent.domains.mapping.types import CsmarTableCandidate
from stata_agent.domains.mapping.types import CsmarTableRecord
from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import CsmarTableSearchRequest
from stata_agent.domains.mapping.types import VariableMatchDecision
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.services.variable_requirements_builder import VariableRequirementsBuilder


class FakeMetadataProvider:
    def __init__(
        self,
        *,
        tables: dict[str, list[CsmarTableCandidate]],
        schemas: dict[str, CsmarTableSchema],
        search_hits: dict[str, list[CsmarFieldSearchHit]] | None = None,
    ) -> None:
        self._tables = tables
        self._schemas = schemas
        self._search_hits = search_hits or {}
        self.search_tables_calls: list[CsmarTableSearchRequest] = []
        self.list_databases_calls = 0
        self.list_tables_calls: list[str] = []
        self.get_table_schema_calls: list[str] = []
        self.search_fields_calls: list[CsmarFieldSearchRequest] = []

    def list_databases(self) -> list[str]:
        self.list_databases_calls += 1
        return sorted({item.database_name for values in self._tables.values() for item in values})

    def list_tables(self, database_name: str) -> list[CsmarTableRecord]:
        self.list_tables_calls.append(database_name)
        records: list[CsmarTableRecord] = []
        for values in self._tables.values():
            for item in values:
                if item.database_name != database_name:
                    continue
                records.append(
                    CsmarTableRecord(
                        table_code=item.table_code,
                        table_name=item.table_name,
                        database_name=item.database_name,
                    )
                )
        return records

    def search_tables(self, request: CsmarTableSearchRequest) -> list[CsmarTableCandidate]:
        self.search_tables_calls.append(request)
        for key, items in self._tables.items():
            if key in request.query:
                return list(items)
        return []

    def get_table_schema(self, table_code: str) -> CsmarTableSchema:
        self.get_table_schema_calls.append(table_code)
        return self._schemas.get(
            table_code,
            CsmarTableSchema(table_code=table_code, fields=[]),
        )

    def search_fields(self, request: CsmarFieldSearchRequest) -> list[CsmarFieldSearchHit]:
        self.search_fields_calls.append(request)
        for key, items in self._search_hits.items():
            if key in request.query:
                return list(items)
        return []

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        raise AssertionError("变量映射测试不应调用 probe。")


class FakeSemanticJudge:
    def __init__(self, decisions: dict[str, VariableMatchDecision]) -> None:
        self._decisions = decisions

    def judge(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        definition: VariableDefinition,
        candidates: list[CsmarFieldCandidate],
    ) -> VariableMatchDecision:
        return self._decisions[definition.variable_name]


def build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="企业资产规模与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资产总计"],
        entity_scope="A股上市公司",
        time_range="2018-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="企业资产规模与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资产总计"],
        entity_scope="A股上市公司",
        time_start_year=2018,
        time_end_year=2023,
        control_variable_candidates=["资产负债率"],
        analysis_grain_candidates=["firm-year"],
        analysis_frequency_hint="annual",
    )


def build_definitions() -> list[VariableDefinition]:
    builder = VariableRequirementsBuilder()
    return builder.build(build_spec()).variable_definitions


def make_table_candidate(
    table_code: str,
    *,
    table_name: str,
    database_name: str,
    score: float,
) -> CsmarTableCandidate:
    return CsmarTableCandidate(
        table_code=table_code,
        table_name=table_name,
        database_name=database_name,
        score=score,
    )


def make_schema_field(
    field_name: str,
    *,
    field_label: str,
    frequency_tags: list[str],
) -> CsmarSchemaField:
    return CsmarSchemaField(
        field_name=field_name,
        field_label=field_label,
        frequency_tags=frequency_tags,
    )


def make_search_hit(
    *,
    table_code: str,
    table_name: str,
    database_name: str,
    field_name: str,
    field_label: str,
    score: float = 0.88,
    why_matched: str = "字段标签包含查询词",
) -> CsmarFieldSearchHit:
    return CsmarFieldSearchHit(
        table_code=table_code,
        table_name=table_name,
        database_name=database_name,
        field_name=field_name,
        field_label=field_label,
        score=score,
        why_matched=why_matched,
    )

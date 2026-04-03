from __future__ import annotations

from dataclasses import dataclass

from stata_agent.domains.mapping.ports import CsmarMetadataProviderPort
from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest
from stata_agent.domains.mapping.types import CsmarSchemaField
from stata_agent.domains.mapping.types import CsmarTableCandidate
from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import CsmarTableSearchRequest
from stata_agent.domains.mapping.types import VariableMappingBudget
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition


@dataclass(slots=True)
class _BudgetCounter:
    search_tables_left: int
    schema_reads_left: int
    search_fields_left: int

    @classmethod
    def from_budget(cls, budget: VariableMappingBudget) -> "_BudgetCounter":
        return cls(
            search_tables_left=max(0, budget.search_tables_limit),
            schema_reads_left=max(0, budget.schema_reads_limit),
            search_fields_left=max(0, budget.search_fields_limit),
        )

    def consume_search_tables(self) -> bool:
        if self.search_tables_left <= 0:
            return False
        self.search_tables_left -= 1
        return True

    def consume_schema_read(self) -> bool:
        if self.schema_reads_left <= 0:
            return False
        self.schema_reads_left -= 1
        return True

    def consume_search_fields(self) -> bool:
        if self.search_fields_left <= 0:
            return False
        self.search_fields_left -= 1
        return True


class MappingCandidateBuilder:
    def __init__(
        self,
        metadata_provider: CsmarMetadataProviderPort,
        mapping_budget: VariableMappingBudget,
    ) -> None:
        self._metadata_provider = metadata_provider
        self._mapping_budget = mapping_budget

    def collect(
        self,
        *,
        spec: ResearchSpec,
        definition: VariableDefinition,
    ) -> tuple[list[CsmarFieldCandidate], list[str]]:
        budget = _BudgetCounter.from_budget(self._mapping_budget)
        warnings: list[str] = []
        search_query = definition.variable_name
        topic_hint = spec.topic.strip()
        if topic_hint:
            search_query = f"{definition.variable_name} {topic_hint}"

        table_candidates: list[CsmarTableCandidate] = []
        if budget.consume_search_tables():
            table_candidates = self._metadata_provider.search_tables(
                CsmarTableSearchRequest(
                    query=search_query,
                    limit=5,
                )
            )
        else:
            warnings.append(f"变量 `{definition.variable_name}` 的 search_tables 预算已耗尽。")

        schemas: dict[str, CsmarTableSchema] = {}
        candidates: list[CsmarFieldCandidate] = []
        seen: set[tuple[str, str]] = set()

        for table in table_candidates:
            if not budget.consume_schema_read():
                warnings.append(f"变量 `{definition.variable_name}` 的 get_table_schema 预算已耗尽。")
                break
            schema = self._metadata_provider.get_table_schema(table.table_code)
            schemas[table.table_code] = schema
            self._extend_candidates_from_schema(
                candidates=candidates,
                seen=seen,
                definition=definition,
                table=table,
                schema=schema,
                source="mcp_schema",
                inherited_evidence=[],
            )

        needs_aux_search = (
            self._mapping_budget.enable_aux_field_search and len(candidates) < 3
        )
        if needs_aux_search:
            if budget.consume_search_fields():
                search_hits = self._metadata_provider.search_fields(
                    CsmarFieldSearchRequest(
                        query=definition.variable_name,
                        role_hint=definition.role,
                        frequency_hint=definition.frequency_hint,
                        limit=20,
                    )
                )
                for hit in search_hits:
                    schema = schemas.get(hit.table_code)
                    if schema is None:
                        if not budget.consume_schema_read():
                            warnings.append(
                                f"变量 `{definition.variable_name}` 的辅助 search_fields 命中未能完成 schema 复核（预算耗尽）。"
                            )
                            break
                        schema = self._metadata_provider.get_table_schema(hit.table_code)
                        schemas[hit.table_code] = schema
                    table_candidate = CsmarTableCandidate(
                        table_code=hit.table_code,
                        table_name=hit.table_name,
                        database_name=hit.database_name,
                        score=hit.score,
                        why_matched=hit.why_matched,
                    )
                    self._extend_candidates_from_schema(
                        candidates=candidates,
                        seen=seen,
                        definition=definition,
                        table=table_candidate,
                        schema=schema,
                        source="mcp_search_fields_verified",
                        inherited_evidence=[
                            f"search_fields命中={hit.field_name}",
                            hit.why_matched,
                        ],
                        restrict_field_name=hit.field_name,
                    )
            else:
                warnings.append(f"变量 `{definition.variable_name}` 的 search_fields 预算已耗尽。")

        ranked = sorted(
            candidates,
            key=lambda item: (
                item.alias_hit,
                definition.frequency_hint in item.frequency_tags,
                bool(item.field_label),
                len(item.match_evidence),
            ),
            reverse=True,
        )
        return ranked[:12], warnings

    def _extend_candidates_from_schema(
        self,
        *,
        candidates: list[CsmarFieldCandidate],
        seen: set[tuple[str, str]],
        definition: VariableDefinition,
        table: CsmarTableCandidate,
        schema: CsmarTableSchema,
        source: str,
        inherited_evidence: list[str],
        restrict_field_name: str | None = None,
    ) -> None:
        for field in schema.fields:
            if restrict_field_name is not None and field.field_name != restrict_field_name:
                continue
            score, alias_hit, evidence = self._score_schema_field(
                variable_name=definition.variable_name,
                field=field,
            )
            if score <= 0 and restrict_field_name is None:
                continue
            if score <= 0 and restrict_field_name is not None:
                evidence.append("search_fields辅助候选已通过schema复核")
            key = (table.table_code, field.field_name)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                CsmarFieldCandidate(
                    variable_name=definition.variable_name,
                    table_code=table.table_code,
                    field_name=field.field_name,
                    database_name=table.database_name,
                    alias_hit=alias_hit,
                    table_name=table.table_name,
                    table_label=table.table_name,
                    field_label=field.field_label,
                    field_description=field.field_description,
                    match_evidence=self._merge_evidence(
                        inherited_evidence=inherited_evidence,
                        local_evidence=evidence,
                        table_match=table.why_matched,
                    ),
                    frequency_tags=field.frequency_tags,
                    catalog_source=source,
                )
            )

    def _merge_evidence(
        self,
        *,
        inherited_evidence: list[str],
        local_evidence: list[str],
        table_match: str,
    ) -> list[str]:
        merged = [*inherited_evidence, *local_evidence]
        if table_match:
            merged.append(f"table_match={table_match}")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in merged:
            text = item.strip()
            if not text or text in seen:
                continue
            deduped.append(text)
            seen.add(text)
        return deduped

    def _score_schema_field(
        self,
        *,
        variable_name: str,
        field: CsmarSchemaField,
    ) -> tuple[int, bool, list[str]]:
        normalized_variable = variable_name.strip().lower()
        normalized_field_name = field.field_name.strip().lower()
        normalized_field_label = field.field_label.strip().lower()
        normalized_field_description = field.field_description.strip().lower()

        score = 0
        alias_hit = False
        evidence: list[str] = []

        if not normalized_variable:
            return score, alias_hit, evidence

        if normalized_variable == normalized_field_name:
            score += 8
            alias_hit = True
            evidence.append("字段代码精确匹配变量名")
        elif normalized_variable in normalized_field_name:
            score += 5
            evidence.append("字段代码包含变量名")

        if normalized_variable and normalized_variable == normalized_field_label:
            score += 8
            alias_hit = True
            evidence.append("字段标签精确匹配变量名")
        elif normalized_variable and normalized_variable in normalized_field_label:
            score += 6
            evidence.append("字段标签包含变量名")

        if normalized_variable and normalized_variable in normalized_field_description:
            score += 2
            evidence.append("字段描述包含变量名")

        return score, alias_hit, evidence

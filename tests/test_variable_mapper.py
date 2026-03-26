from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.services.variable_mapper import VariableMapper


class MetadataProviderWithCoverage:
    def __init__(self, *, missing_fields: set[str] | None = None) -> None:
        self._missing_fields = missing_fields or set()

    def find_field_candidates(self, variable_name: str) -> list[CsmarFieldCandidate]:
        mapping = {
            "ROA": CsmarFieldCandidate(
                variable_name="ROA",
                table_name="FS_Comins",
                field_name="ROA",
                csmar_database="财务报表",
                alias_hit=True,
                frequency_tags=["annual", "quarterly"],
            ),
            "数字化转型指数": CsmarFieldCandidate(
                variable_name="数字化转型指数",
                table_name="BANK_DIGITAL_INDEX",
                field_name="DIGITAL_INDEX",
                csmar_database="银行专题",
                alias_hit=True,
                frequency_tags=["annual", "quarterly"],
            ),
            "资本充足率": CsmarFieldCandidate(
                variable_name="资本充足率",
                table_name="FS_Combas",
                field_name="CAPITAL_ADEQUACY",
                csmar_database="财务报表",
                alias_hit=True,
                frequency_tags=["annual", "quarterly"],
            ),
        }
        candidate = mapping.get(variable_name)
        return [candidate] if candidate is not None else []

    def field_exists(self, table_name: str, field_name: str) -> bool:
        return field_name not in self._missing_fields


def _build_request(empirical_requirements: str = "构建基准回归模型") -> ResearchRequest:
    return ResearchRequest(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_range="2010-2023",
        empirical_requirements=empirical_requirements,
    )


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_start_year=2010,
        time_end_year=2023,
        control_variable_candidates=["资本充足率"],
        analysis_grain_candidates=["bank-year"],
    )


def _build_definitions() -> list[VariableDefinition]:
    return [
        VariableDefinition(
            variable_name="ROA",
            role="dependent",
            is_locked=True,
            slot_status="ready",
            frequency_hint="annual",
            source_domain_hint="finance_statement",
        ),
        VariableDefinition(
            variable_name="数字化转型指数",
            role="independent",
            is_locked=True,
            slot_status="ready",
            frequency_hint="annual",
            source_domain_hint="digital_topic",
        ),
        VariableDefinition(
            variable_name="资本充足率",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
            source_domain_hint="finance_statement",
        ),
    ]


def test_mapper_generates_non_empty_bindings_for_y_and_x() -> None:
    mapper = VariableMapper(metadata_provider=MetadataProviderWithCoverage())

    result = mapper.map_probe_bindings(_build_request(), _build_spec(), _build_definitions())

    assert result.failure_reason is None
    assert result.bindings
    names = {binding.variable_name for binding in result.bindings}
    assert "ROA" in names
    assert "数字化转型指数" in names


def test_mapper_fails_fast_when_hard_contract_field_missing() -> None:
    mapper = VariableMapper(
        metadata_provider=MetadataProviderWithCoverage(missing_fields={"ROA"})
    )

    result = mapper.map_probe_bindings(
        _build_request(empirical_requirements="必须包含资本充足率"),
        _build_spec(),
        _build_definitions(),
    )

    assert result.failure_reason is not None
    assert "ROA" in result.failure_reason
    assert result.bindings == []


def test_mapper_keeps_soft_gap_summary_without_aborting() -> None:
    mapper = VariableMapper(metadata_provider=MetadataProviderWithCoverage())
    definitions = [
        item
        for item in _build_definitions()
        if item.variable_name != "资本充足率"
    ]
    definitions.append(
        VariableDefinition(
            variable_name="拨备覆盖率",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
            source_domain_hint="bank_topic",
        )
    )

    result = mapper.map_probe_bindings(_build_request(), _build_spec(), definitions)

    assert result.failure_reason is None
    assert "拨备覆盖率" in result.soft_contract_gaps
    assert result.warnings

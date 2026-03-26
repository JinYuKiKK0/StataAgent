from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.providers.csmar import CsmarMetadataError
from stata_agent.services.probe_executor import ProbeExecutor


class ProbeProviderStub:
    def __init__(
        self,
        *,
        missing_fields: set[tuple[str, str]] | None = None,
        zero_count_fields: set[tuple[str, str]] | None = None,
        inaccessible_fields: set[tuple[str, str]] | None = None,
    ) -> None:
        self._missing_fields = missing_fields or set()
        self._zero_count_fields = zero_count_fields or set()
        self._inaccessible_fields = inaccessible_fields or set()

    def find_field_candidates(self, variable_name: str) -> list[CsmarFieldCandidate]:
        return []

    def field_exists(self, table_name: str, field_name: str) -> bool:
        return (table_name, field_name) not in self._missing_fields

    def query_count(self, table_name: str, field_name: str) -> int:
        key = (table_name, field_name)
        if key in self._inaccessible_fields:
            raise CsmarMetadataError("queryCount 调用失败")
        if key in self._zero_count_fields:
            return 0
        return 100


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


def _build_bindings() -> list[VariableBinding]:
    return [
        VariableBinding(
            variable_name="ROA",
            table_name="FS_Comins",
            field_name="ROA",
            confidence=0.9,
            csmar_database="财务报表",
            contract_tier="hard",
            is_hard_contract=True,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
        ),
        VariableBinding(
            variable_name="数字化转型指数",
            table_name="BANK_DIGITAL_INDEX",
            field_name="DIGITAL_INDEX",
            confidence=0.9,
            csmar_database="银行专题",
            contract_tier="hard",
            is_hard_contract=True,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
        ),
        VariableBinding(
            variable_name="资本充足率",
            table_name="FS_Combas",
            field_name="CAPITAL_ADEQUACY",
            confidence=0.8,
            csmar_database="财务报表",
            contract_tier="soft",
            is_hard_contract=False,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
        ),
    ]


def test_probe_executor_reports_successful_coverage() -> None:
    executor = ProbeExecutor(metadata_provider=ProbeProviderStub())

    result = executor.execute_coverage(_build_spec(), _build_bindings())

    assert result.failure_reason is None
    assert result.hard_coverage_rate == 1.0
    assert result.soft_coverage_rate == 1.0
    assert result.key_alignment_ready is True
    assert result.target_grain_ready is True


def test_probe_executor_fails_fast_on_hard_contract_gap() -> None:
    provider = ProbeProviderStub(missing_fields={("FS_Comins", "ROA")})
    executor = ProbeExecutor(metadata_provider=provider)

    result = executor.execute_coverage(_build_spec(), _build_bindings())

    assert result.failure_reason is not None
    assert "Hard Contract" in result.failure_reason
    assert "ROA" in result.hard_gaps


def test_probe_executor_keeps_soft_gap_without_aborting() -> None:
    provider = ProbeProviderStub(zero_count_fields={("FS_Combas", "CAPITAL_ADEQUACY")})
    executor = ProbeExecutor(metadata_provider=provider)

    result = executor.execute_coverage(_build_spec(), _build_bindings())

    assert result.failure_reason is None
    assert "资本充足率" in result.soft_gaps
    assert result.warnings

"""S1-T5 探针执行与覆盖摘要测试。"""

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.mapping.contracts import CsmarFieldProbeRequest
from stata_agent.services.mapping.contracts import CsmarFieldProbeResult
from stata_agent.services.mapping.contracts import CsmarTableRecord
from stata_agent.services.mapping.contracts import CsmarTableSchema
from stata_agent.services.probe.contracts import ProbeCoverageResult
from stata_agent.services.probe.executor import ProbeExecutor
from stata_agent.services.probe.summarizer import ProbeCoverageSummarizer


class _FakeMetadataProvider:
    def __init__(
        self,
        results: dict[tuple[str, str], CsmarFieldProbeResult],
    ) -> None:
        self._results = results
        self.probe_calls: list[tuple[str, str]] = []

    def list_databases(self) -> list[str]:
        raise AssertionError("探针测试不应调用数据库枚举。")

    def list_tables(self, database_name: str) -> list[CsmarTableRecord]:
        raise AssertionError("探针测试不应调用表枚举。")

    def get_table_schema(self, table_code: str) -> CsmarTableSchema:
        raise AssertionError("探针测试不应调用 schema 读取。")

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        key = (request.table_code, request.field_name)
        self.probe_calls.append(key)
        return self._results[key]


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="银行资本充足率与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_start_year=2018,
        time_end_year=2023,
        control_variable_candidates=[],
        analysis_grain_candidates=["bank-year"],
    )


def _build_hard_binding() -> VariableBinding:
    return VariableBinding(
        variable_name="ROA",
        table_code="FS_Comins",
        field_name="ROA",
        confidence=0.9,
        database_name="财务报表",
        contract_tier="hard",
        is_hard_contract=True,
        frequency_match=True,
        source="unit-test",
        evidence="hard",
        table_name="利润表",
    )


def _execute_probe_summary(
    executor: ProbeExecutor,
    variable_bindings: list[VariableBinding],
) -> ProbeCoverageResult:
    probe_results = executor.run_field_probes(_build_spec(), variable_bindings)
    return ProbeCoverageSummarizer().summarize_coverage(_build_spec(), probe_results)


def test_probe_executor_reports_scoped_coverage() -> None:
    """验证探针节点会保留时间范围 scoped probe 的结果与指纹。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_code="FS_Comins",
                field_name="ROA",
                field_exists=True,
                row_count=1280,
                query_fingerprint="FS_Comins.ROA:2018-2023",
                validation_id="validation_probe_roa",
                scope_level="time_scoped",
            )
        }
    )
    executor = ProbeExecutor(metadata_provider=provider)

    result = _execute_probe_summary(executor, [_build_hard_binding()])

    assert result.failure_reason is None
    assert result.hard_coverage_rate == 1.0
    assert result.probe_results[0].query_fingerprint == "FS_Comins.ROA:2018-2023"


def test_probe_executor_fails_fast_for_hard_gap() -> None:
    """验证 Hard Contract 字段不可达时会触发 fail-fast。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_code="FS_Comins",
                field_name="ROA",
                field_exists=False,
                query_fingerprint="FS_Comins.ROA:2018-2023",
                scope_level="time_scoped",
            )
        }
    )
    executor = ProbeExecutor(metadata_provider=provider)

    result = _execute_probe_summary(executor, [_build_hard_binding()])

    assert result.failure_reason is not None
    assert result.hard_gaps == ["ROA"]




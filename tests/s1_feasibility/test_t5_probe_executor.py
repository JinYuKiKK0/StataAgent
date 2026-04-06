"""S1-T5 探针执行与覆盖摘要测试。"""

from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarTableRecord
from stata_agent.domains.mapping.types import CsmarTableSchema
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.providers.csmar import CsmarMetadataError
from stata_agent.services.probe_executor import ProbeExecutor


class _FakeMetadataProvider:
    def __init__(
        self,
        results: dict[tuple[str, str], CsmarFieldProbeResult],
        *,
        raise_on: tuple[str, str] | None = None,
    ) -> None:
        self._results = results
        self._raise_on = raise_on
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
        if self._raise_on == key:
            raise CsmarMetadataError(
                "CSMAR 探针命中冷却限制。",
                code="rate_limited",
                retriable=True,
                vendor_message="30分钟限制",
                hint="等待冷却后重试。",
                retry_after_seconds=60,
            )
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


def _build_soft_invalid_binding() -> VariableBinding:
    return VariableBinding(
        variable_name="软约束不存在字段",
        table_code="FS_Comins",
        field_name="NOT_A_REAL_FIELD_SOFT",
        confidence=0.1,
        database_name="财务报表",
        contract_tier="soft",
        is_hard_contract=False,
        frequency_match=True,
        source="unit-test",
        evidence="soft-gap",
        table_name="利润表",
    )


def _execute_probe_summary(
    executor: ProbeExecutor,
    variable_bindings: list[VariableBinding],
) -> ProbeCoverageResult:
    probe_results = executor.run_field_probes(_build_spec(), variable_bindings)
    return executor.summarize_coverage(_build_spec(), probe_results)


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
    assert result.probe_results[0].validation_id == "validation_probe_roa"
    assert any("时间范围 probe" in warning for warning in result.warnings)


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


def test_probe_executor_keeps_soft_gap_summary_without_abort() -> None:
    """验证 Soft Contract 缺口只会被记录，探针阶段仍允许继续。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_code="FS_Comins",
                field_name="ROA",
                field_exists=True,
                row_count=1280,
                query_fingerprint="FS_Comins.ROA:2018-2023",
                scope_level="time_scoped",
            ),
            ("FS_Comins", "NOT_A_REAL_FIELD_SOFT"): CsmarFieldProbeResult(
                variable_name="软约束不存在字段",
                table_code="FS_Comins",
                field_name="NOT_A_REAL_FIELD_SOFT",
                field_exists=False,
                query_fingerprint="FS_Comins.NOT_A_REAL_FIELD_SOFT:2018-2023",
                scope_level="time_scoped",
            ),
        }
    )
    executor = ProbeExecutor(metadata_provider=provider)

    result = _execute_probe_summary(
        executor,
        [_build_hard_binding(), _build_soft_invalid_binding()],
    )

    assert result.failure_reason is None
    assert "软约束不存在字段" in result.soft_gaps


def test_probe_executor_surfaces_vendor_cooldown_errors() -> None:
    """验证供应商冷却限制会作为可审计失败原因进入 probe 结果。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_code="FS_Comins",
                field_name="ROA",
                field_exists=True,
                row_count=1,
                query_fingerprint="FS_Comins.ROA:2018-2023",
                scope_level="time_scoped",
            )
        },
        raise_on=("FS_Comins", "ROA"),
    )
    executor = ProbeExecutor(metadata_provider=provider)

    result = _execute_probe_summary(executor, [_build_hard_binding()])

    assert result.failure_reason is not None
    assert result.probe_results[0].vendor_message == "30分钟限制"


def test_probe_executor_deduplicates_same_probe_key_calls() -> None:
    """验证相同 table_code/field_name/time_range 只会触发一次真实 probe 调用。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_code="FS_Comins",
                field_name="ROA",
                field_exists=True,
                row_count=99,
                query_fingerprint="FS_Comins.ROA:2018-2023",
                scope_level="time_scoped",
            )
        }
    )
    executor = ProbeExecutor(metadata_provider=provider)
    second_binding = _build_hard_binding().model_copy(
        update={
            "variable_name": "ROA_副本",
            "contract_tier": "soft",
            "is_hard_contract": False,
            "trace_id": "trace_custom",
        }
    )

    result = _execute_probe_summary(executor, [_build_hard_binding(), second_binding])

    assert len(provider.probe_calls) == 1
    assert len(result.probe_results) == 2
    assert result.probe_results[1].variable_name == "ROA_副本"
    assert result.probe_results[1].trace_id == "trace_custom"


def test_probe_executor_surfaces_fail_fast_error_metadata() -> None:
    """验证 fail-fast 错误码会透传到 probe 结果并写入提示。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_code="FS_Comins",
                field_name="ROA",
                field_exists=True,
            )
        },
        raise_on=("FS_Comins", "ROA"),
    )
    executor = ProbeExecutor(metadata_provider=provider)

    result = _execute_probe_summary(executor, [_build_hard_binding()])

    assert result.failure_reason is not None
    assert result.probe_results[0].error_code == "rate_limited"
    assert result.probe_results[0].retry_after_seconds == 60
    assert any("fail-fast" in warning for warning in result.warnings)

"""S1-T5 探针执行与覆盖摘要测试。"""

import pytest

from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.providers.csmar import CsmarMetadataError
from stata_agent.services.probe_executor import ProbeExecutor
from stata_agent.services.requirement_parser import RequirementParser

pytest_plugins = ["tests.live_api_support"]


class _FakeMetadataProvider:
    def __init__(
        self,
        results: dict[tuple[str, str], CsmarFieldProbeResult],
        *,
        raise_on: tuple[str, str] | None = None,
    ) -> None:
        self._results = results
        self._raise_on = raise_on

    def search_field_candidates(
        self, request: CsmarFieldSearchRequest
    ) -> list[CsmarFieldCandidate]:
        raise AssertionError("探针测试不应调用字段搜索。")

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        key = (request.table_name, request.field_name)
        if self._raise_on == key:
            raise CsmarMetadataError(
                "CSMAR 探针命中冷却限制。", retriable=True, vendor_message="30分钟限制"
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
        table_name="FS_Comins",
        field_name="ROA",
        confidence=0.9,
        csmar_database="财务报表",
        contract_tier="hard",
        is_hard_contract=True,
        frequency_match=True,
        source="unit-test",
        evidence="hard",
    )


def _build_soft_invalid_binding() -> VariableBinding:
    return VariableBinding(
        variable_name="软约束不存在字段",
        table_name="FS_Comins",
        field_name="NOT_A_REAL_FIELD_SOFT",
        confidence=0.1,
        csmar_database="财务报表",
        contract_tier="soft",
        is_hard_contract=False,
        frequency_match=True,
        source="unit-test",
        evidence="soft-gap",
    )


def test_probe_executor_reports_scoped_coverage() -> None:
    """验证探针节点会保留时间范围 scoped probe 的结果与指纹。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_name="FS_Comins",
                field_name="ROA",
                field_exists=True,
                row_count=1280,
                query_fingerprint="FS_Comins.ROA:2018-2023",
                scope_level="time_scoped",
            )
        }
    )
    executor = ProbeExecutor(metadata_provider=provider)

    result = executor.execute_coverage(_build_spec(), [_build_hard_binding()])

    assert result.failure_reason is None
    assert result.hard_coverage_rate == 1.0
    assert result.probe_results[0].query_fingerprint == "FS_Comins.ROA:2018-2023"
    assert any("时间范围 probe" in warning for warning in result.warnings)


def test_probe_executor_fails_fast_for_hard_gap() -> None:
    """验证 Hard Contract 字段不可达时会触发 fail-fast。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_name="FS_Comins",
                field_name="ROA",
                field_exists=False,
                query_fingerprint="FS_Comins.ROA:2018-2023",
                scope_level="time_scoped",
            )
        }
    )
    executor = ProbeExecutor(metadata_provider=provider)

    result = executor.execute_coverage(_build_spec(), [_build_hard_binding()])

    assert result.failure_reason is not None
    assert result.hard_gaps == ["ROA"]


def test_probe_executor_keeps_soft_gap_summary_without_abort() -> None:
    """验证 Soft Contract 缺口只会被记录，探针阶段仍允许继续。"""
    provider = _FakeMetadataProvider(
        {
            ("FS_Comins", "ROA"): CsmarFieldProbeResult(
                variable_name="ROA",
                table_name="FS_Comins",
                field_name="ROA",
                field_exists=True,
                row_count=1280,
                query_fingerprint="FS_Comins.ROA:2018-2023",
                scope_level="time_scoped",
            ),
            ("FS_Comins", "NOT_A_REAL_FIELD_SOFT"): CsmarFieldProbeResult(
                variable_name="软约束不存在字段",
                table_name="FS_Comins",
                field_name="NOT_A_REAL_FIELD_SOFT",
                field_exists=False,
                query_fingerprint="FS_Comins.NOT_A_REAL_FIELD_SOFT:2018-2023",
                scope_level="time_scoped",
            ),
        }
    )
    executor = ProbeExecutor(metadata_provider=provider)

    result = executor.execute_coverage(
        _build_spec(),
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
                table_name="FS_Comins",
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

    result = executor.execute_coverage(_build_spec(), [_build_hard_binding()])

    assert result.failure_reason is not None
    assert result.probe_results[0].vendor_message == "30分钟限制"


@pytest.mark.live_api
def test_probe_executor_reports_real_coverage(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证探针节点会使用真实 CSMAR queryCount 返回覆盖摘要。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None

    executor = ProbeExecutor(metadata_provider=live_csmar_provider)
    result = executor.execute_coverage(parse_result.spec, [_build_hard_binding()])

    assert result.failure_reason is None
    assert result.hard_coverage_rate == 1.0
    assert result.key_alignment_ready is True


@pytest.mark.live_api
def test_probe_executor_fails_fast_for_real_hard_gap(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_request: ResearchRequest,
) -> None:
    """验证真实探针中 Hard Contract 字段不可达时会触发 fail-fast。"""
    parse_result = live_parser.parse(live_request)
    assert parse_result.spec is not None

    executor = ProbeExecutor(metadata_provider=live_csmar_provider)
    invalid_binding = _build_hard_binding().model_copy(
        update={"field_name": "NOT_A_REAL_FIELD", "variable_name": "硬约束不存在字段"}
    )
    result = executor.execute_coverage(parse_result.spec, [invalid_binding])

    assert result.failure_reason is not None
    assert result.hard_gaps == ["硬约束不存在字段"]

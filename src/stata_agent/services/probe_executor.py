from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.fetch.types import VariableProbeResult
from stata_agent.domains.mapping.ports import CsmarMetadataProviderPort
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.providers.csmar import CsmarMetadataError


class ProbeExecutor:
    def __init__(self, metadata_provider: CsmarMetadataProviderPort) -> None:
        self._metadata_provider = metadata_provider

    def execute_coverage(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> ProbeCoverageResult:
        probe_results = [
            self._probe_binding(spec=spec, binding=binding)
            for binding in variable_bindings
        ]
        hard_results = [
            result for result in probe_results if result.contract_tier == "hard"
        ]
        soft_results = [
            result for result in probe_results if result.contract_tier == "soft"
        ]
        hard_gaps = [
            result.variable_name for result in hard_results if not result.is_accessible
        ]
        soft_gaps = [
            result.variable_name for result in soft_results if not result.is_accessible
        ]
        warnings = self._collect_probe_warnings(probe_results)
        warnings.extend(self._build_soft_gap_warnings(soft_gaps))
        key_alignment_ready = all(result.is_accessible for result in hard_results)
        target_grain_ready = self._is_target_grain_ready(spec, hard_results)
        return ProbeCoverageResult(
            probe_results=probe_results,
            hard_coverage_rate=self._coverage_rate(hard_results),
            soft_coverage_rate=self._coverage_rate(soft_results),
            hard_gaps=hard_gaps,
            soft_gaps=soft_gaps,
            key_alignment_ready=key_alignment_ready,
            target_grain_ready=target_grain_ready,
            warnings=warnings,
            failure_reason=self._build_failure_reason(
                hard_gaps=hard_gaps,
                key_alignment_ready=key_alignment_ready,
                target_grain_ready=target_grain_ready,
            ),
        )

    def _probe_binding(
        self,
        *,
        spec: ResearchSpec,
        binding: VariableBinding,
    ) -> VariableProbeResult:
        try:
            probe_result = self._metadata_provider.probe_field_availability(
                CsmarFieldProbeRequest(
                    variable_name=binding.variable_name,
                    table_name=binding.table_name,
                    field_name=binding.field_name,
                    contract_tier=binding.contract_tier,
                    entity_scope=spec.entity_scope,
                    analysis_grain=spec.analysis_grain_candidates[0]
                    if spec.analysis_grain_candidates
                    else "",
                    time_start_year=spec.time_start_year,
                    time_end_year=spec.time_end_year,
                )
            )
        except CsmarMetadataError as exc:
            return self._build_probe_failure(
                binding=binding,
                field_exists=False,
                failure_reason=str(exc),
                query_fingerprint="",
                scope_level="time_scoped",
                vendor_message=exc.vendor_message,
            )

        if not probe_result.field_exists:
            return self._build_probe_failure(
                binding=binding,
                field_exists=False,
                failure_reason="字段不存在，无法执行 scoped probe。",
                query_fingerprint=probe_result.query_fingerprint,
                scope_level=probe_result.scope_level,
                vendor_message=probe_result.vendor_message,
            )
        if probe_result.row_count is None or probe_result.row_count <= 0:
            return self._build_probe_failure(
                binding=binding,
                field_exists=True,
                failure_reason="queryCount 结果为 0，字段在目标时间范围内不可得。",
                query_count=probe_result.row_count,
                query_fingerprint=probe_result.query_fingerprint,
                scope_level=probe_result.scope_level,
                vendor_message=probe_result.vendor_message,
            )
        return self._build_probe_success(binding, probe_result.row_count, probe_result)

    def _build_probe_failure(
        self,
        *,
        binding: VariableBinding,
        field_exists: bool,
        failure_reason: str,
        query_fingerprint: str,
        scope_level: str,
        vendor_message: str,
        query_count: int | None = None,
    ) -> VariableProbeResult:
        return VariableProbeResult(
            variable_name=binding.variable_name,
            contract_tier=binding.contract_tier,
            table_name=binding.table_name,
            field_name=binding.field_name,
            field_exists=field_exists,
            frequency_match=binding.frequency_match,
            query_count=query_count,
            failure_reason=failure_reason,
            query_fingerprint=query_fingerprint,
            scope_level=scope_level,
            vendor_message=vendor_message,
        )

    def _build_probe_success(
        self,
        binding: VariableBinding,
        count: int,
        probe_result: CsmarFieldProbeResult,
    ) -> VariableProbeResult:
        return VariableProbeResult(
            variable_name=binding.variable_name,
            contract_tier=binding.contract_tier,
            table_name=binding.table_name,
            field_name=binding.field_name,
            field_exists=True,
            frequency_match=binding.frequency_match,
            query_count=count,
            is_accessible=True,
            query_fingerprint=probe_result.query_fingerprint,
            scope_level=probe_result.scope_level,
            vendor_message=probe_result.vendor_message,
        )

    def _collect_probe_warnings(
        self, probe_results: list[VariableProbeResult]
    ) -> list[str]:
        warnings: list[str] = []
        for result in probe_results:
            if result.scope_level == "time_scoped":
                warnings.append(
                    f"变量 `{result.variable_name}` 当前仅完成时间范围 probe，样本范围仍待后续验证。"
                )
        return warnings

    def _is_target_grain_ready(
        self,
        spec: ResearchSpec,
        hard_results: list[VariableProbeResult],
    ) -> bool:
        if not hard_results:
            return False
        if not spec.analysis_grain_candidates:
            return True
        annual_required = any(
            "year" in grain.lower() for grain in spec.analysis_grain_candidates
        )
        quarterly_required = any(
            "quarter" in grain.lower() for grain in spec.analysis_grain_candidates
        )
        if annual_required or quarterly_required:
            return all(result.frequency_match for result in hard_results)
        return True

    def _build_failure_reason(
        self,
        *,
        hard_gaps: list[str],
        key_alignment_ready: bool,
        target_grain_ready: bool,
    ) -> str | None:
        if hard_gaps:
            variables = "、".join(hard_gaps)
            return f"探针失败：Hard Contract 变量不可得：{variables}。"
        if not key_alignment_ready:
            return "探针失败：关键主键不可对齐，阻断后续阶段。"
        if not target_grain_ready:
            return "探针失败：目标粒度不可得，Hard Contract 变量频率不匹配。"
        return None

    def _build_soft_gap_warnings(self, soft_gaps: list[str]) -> list[str]:
        if not soft_gaps:
            return []
        text = "、".join(soft_gaps)
        return [f"Soft Contract 变量覆盖不足：{text}。已记录摘要并继续。"]

    def _coverage_rate(self, results: list[VariableProbeResult]) -> float:
        if not results:
            return 1.0
        covered = sum(1 for item in results if item.is_accessible)
        return covered / len(results)

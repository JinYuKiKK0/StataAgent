from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.probe.contracts import ProbeCoverageResult
from stata_agent.services.probe.contracts import VariableProbeResult


class ProbeCoverageSummarizer:
    def summarize_coverage(
        self,
        spec: ResearchSpec,
        probe_results: list[VariableProbeResult],
    ) -> ProbeCoverageResult:
        hard_results = [r for r in probe_results if r.contract_tier == "hard"]
        soft_results = [r for r in probe_results if r.contract_tier == "soft"]
        hard_gaps = [r.variable_name for r in hard_results if not r.is_accessible]
        soft_gaps = [r.variable_name for r in soft_results if not r.is_accessible]
        warnings = self._collect_probe_warnings(probe_results)
        warnings.extend(self._collect_fail_fast_warnings(probe_results))
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

    def _collect_fail_fast_warnings(
        self,
        probe_results: list[VariableProbeResult],
    ) -> list[str]:
        fail_fast_codes = {"table_not_found", "field_not_found", "rate_limited"}
        warnings: list[str] = []
        for result in probe_results:
            if result.error_code not in fail_fast_codes:
                continue
            retry_hint = (
                f" 建议等待 {result.retry_after_seconds}s 后重试。"
                if result.retry_after_seconds is not None
                else ""
            )
            warnings.append(
                f"变量 `{result.variable_name}` 命中 `{result.error_code}`，按 fail-fast 策略不做内部重试。{retry_hint}"
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

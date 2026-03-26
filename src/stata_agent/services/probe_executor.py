from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.fetch.types import VariableProbeResult
from stata_agent.domains.mapping.ports import CsmarMetadataProviderPort
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
        probe_results = [self._probe_binding(binding) for binding in variable_bindings]
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
        hard_coverage_rate = self._coverage_rate(hard_results)
        soft_coverage_rate = self._coverage_rate(soft_results)

        key_alignment_ready = not hard_gaps
        target_grain_ready = self._is_target_grain_ready(spec, hard_results)
        failure_reason = self._build_failure_reason(
            hard_gaps, key_alignment_ready, target_grain_ready
        )

        return ProbeCoverageResult(
            probe_results=probe_results,
            hard_coverage_rate=hard_coverage_rate,
            soft_coverage_rate=soft_coverage_rate,
            hard_gaps=hard_gaps,
            soft_gaps=soft_gaps,
            key_alignment_ready=key_alignment_ready,
            target_grain_ready=target_grain_ready,
            warnings=self._build_soft_gap_warnings(soft_gaps),
            failure_reason=failure_reason,
        )

    def _probe_binding(self, binding: VariableBinding) -> VariableProbeResult:
        if not self._metadata_provider.field_exists(
            binding.table_name, binding.field_name
        ):
            return self._build_probe_failure(
                binding,
                field_exists=False,
                failure_reason="字段不存在，无法执行 queryCount 探针。",
            )

        try:
            count = self._metadata_provider.query_count(
                binding.table_name, binding.field_name
            )
        except CsmarMetadataError as exc:
            return self._build_probe_failure(
                binding,
                field_exists=True,
                failure_reason=str(exc),
            )

        if count <= 0:
            return self._build_probe_failure(
                binding,
                field_exists=True,
                failure_reason="queryCount 结果为 0，字段在目标范围内不可得。",
                query_count=count,
            )

        return self._build_probe_success(binding, count)

    def _build_probe_failure(
        self,
        binding: VariableBinding,
        *,
        field_exists: bool,
        failure_reason: str,
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
        )

    def _build_probe_success(
        self, binding: VariableBinding, count: int
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
        )

    def _is_target_grain_ready(
        self,
        spec: ResearchSpec,
        hard_results: list[VariableProbeResult],
    ) -> bool:
        if not hard_results:
            return False
        if not spec.analysis_grain_candidates:
            return True
        if any("year" in grain.lower() for grain in spec.analysis_grain_candidates):
            return all(result.frequency_match for result in hard_results)
        return True

    def _build_failure_reason(
        self,
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

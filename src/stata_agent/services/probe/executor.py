from __future__ import annotations

from typing import cast

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.services.mapping.contracts import CsmarFieldProbeRequest
from stata_agent.services.mapping.contracts import CsmarFieldProbeResult
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.probe.contracts import ProbeExecutionInput
from stata_agent.services.probe.contracts import VariableProbeResult


class ProbeExecutor:
    def __init__(self, metadata_provider: CsmarMetadataProviderPort) -> None:
        self._metadata_provider = metadata_provider
        self._pending_traces: list[object] = []

    def run_field_probes(
        self,
        probe_input: ProbeExecutionInput,
    ) -> list[VariableProbeResult]:
        self._pending_traces = []
        probe_results: list[VariableProbeResult] = []
        probe_cache: dict[tuple[str, str, int, int], VariableProbeResult] = {}
        for binding in probe_input.variable_bindings:
            probe_key = (
                binding.table_code,
                binding.field_name,
                probe_input.time_start_year,
                probe_input.time_end_year,
            )
            cached = probe_cache.get(probe_key)
            if cached is None:
                result = self._probe_binding(probe_input=probe_input, binding=binding)
                probe_cache[probe_key] = result
                probe_results.append(result)
                continue

            probe_results.append(
                cached.model_copy(
                    update={
                        "variable_name": binding.variable_name,
                        "contract_tier": binding.contract_tier,
                        "frequency_match": binding.frequency_match,
                        "trace_id": cached.trace_id,
                    }
                )
            )
        return probe_results

    def _probe_binding(
        self,
        *,
        probe_input: ProbeExecutionInput,
        binding: VariableBinding,
    ) -> VariableProbeResult:
        trace_id = ""
        try:
            probe_result = self._metadata_provider.probe_field_availability(
                CsmarFieldProbeRequest(
                    variable_name=binding.variable_name,
                    table_code=binding.table_code,
                    field_name=binding.field_name,
                    contract_tier=binding.contract_tier,
                    entity_scope=probe_input.entity_scope,
                    analysis_grain=probe_input.analysis_grain,
                    time_start_year=probe_input.time_start_year,
                    time_end_year=probe_input.time_end_year,
                )
            )
        except Exception as exc:
            provider_traces = self._drain_provider_traces()
            self._pending_traces.extend(provider_traces)
            trace_id = self._last_trace_id(provider_traces, trace_id)
            return self._build_probe_failure(
                binding=binding,
                field_exists=False,
                failure_reason=str(exc),
                trace_id=trace_id,
                query_fingerprint="",
                validation_id="",
                scope_level="time_scoped",
                vendor_message=str(getattr(exc, "vendor_message", str(exc))),
                error_code=str(getattr(exc, "code", "")),
                hint=str(getattr(exc, "hint", "")),
                retry_after_seconds=getattr(exc, "retry_after_seconds", None),
                suggested_args_patch=getattr(exc, "suggested_args_patch", None),
            )

        provider_traces = self._drain_provider_traces()
        self._pending_traces.extend(provider_traces)
        trace_id = self._last_trace_id(provider_traces, trace_id)

        if not probe_result.field_exists:
            return self._build_probe_failure(
                binding=binding,
                field_exists=False,
                failure_reason="字段不存在，无法执行 scoped probe。",
                trace_id=trace_id,
                query_fingerprint=probe_result.query_fingerprint,
                validation_id=probe_result.validation_id,
                scope_level=probe_result.scope_level,
                vendor_message=probe_result.vendor_message,
                error_code=probe_result.error_code or "field_not_found",
                hint=probe_result.hint or "字段不存在，建议先读取表结构后修正字段代码。",
                retry_after_seconds=probe_result.retry_after_seconds,
                suggested_args_patch=probe_result.suggested_args_patch,
            )
        if probe_result.row_count is None or probe_result.row_count <= 0:
            return self._build_probe_failure(
                binding=binding,
                field_exists=True,
                failure_reason="queryCount 结果为 0，字段在目标时间范围内不可得。",
                trace_id=trace_id,
                query_count=probe_result.row_count,
                query_fingerprint=probe_result.query_fingerprint,
                validation_id=probe_result.validation_id,
                scope_level=probe_result.scope_level,
                vendor_message=probe_result.vendor_message,
                error_code=probe_result.error_code,
                hint=probe_result.hint,
                retry_after_seconds=probe_result.retry_after_seconds,
                suggested_args_patch=probe_result.suggested_args_patch,
            )
        return self._build_probe_success(
            binding,
            probe_result.row_count,
            probe_result,
            trace_id=trace_id,
        )

    def _build_probe_failure(
        self,
        *,
        binding: VariableBinding,
        field_exists: bool,
        failure_reason: str,
        trace_id: str,
        query_fingerprint: str,
        validation_id: str,
        scope_level: str,
        vendor_message: str,
        query_count: int | None = None,
        error_code: str = "",
        hint: str = "",
        retry_after_seconds: int | None = None,
        suggested_args_patch: dict[str, object] | None = None,
    ) -> VariableProbeResult:
        return VariableProbeResult(
            variable_name=binding.variable_name,
            contract_tier=binding.contract_tier,
            table_code=binding.table_code,
            field_name=binding.field_name,
            field_exists=field_exists,
            frequency_match=binding.frequency_match,
            query_count=query_count,
            failure_reason=failure_reason,
            trace_id=trace_id,
            query_fingerprint=query_fingerprint,
            validation_id=validation_id,
            scope_level=scope_level,
            vendor_message=vendor_message,
            error_code=error_code,
            hint=hint,
            retry_after_seconds=retry_after_seconds,
            suggested_args_patch=suggested_args_patch,
        )

    def _build_probe_success(
        self,
        binding: VariableBinding,
        count: int,
        probe_result: CsmarFieldProbeResult,
        *,
        trace_id: str,
    ) -> VariableProbeResult:
        return VariableProbeResult(
            variable_name=binding.variable_name,
            contract_tier=binding.contract_tier,
            table_code=binding.table_code,
            field_name=binding.field_name,
            field_exists=True,
            frequency_match=binding.frequency_match,
            query_count=count,
            is_accessible=True,
            trace_id=trace_id,
            query_fingerprint=probe_result.query_fingerprint,
            validation_id=probe_result.validation_id,
            scope_level=probe_result.scope_level,
            vendor_message=probe_result.vendor_message,
            error_code=probe_result.error_code,
            hint=probe_result.hint,
            retry_after_seconds=probe_result.retry_after_seconds,
            suggested_args_patch=probe_result.suggested_args_patch,
        )

    def drain_tool_traces(self) -> list[object]:
        traces = list(self._pending_traces)
        self._pending_traces.clear()
        return traces

    def _drain_provider_traces(self) -> list[object]:
        drain = getattr(self._metadata_provider, "drain_tool_traces", None)
        if not callable(drain):
            return []
        raw_traces = drain()
        if not isinstance(raw_traces, list):
            return []
        return cast(list[object], raw_traces)

    def _last_trace_id(
        self,
        provider_traces: list[object],
        fallback_trace_id: str,
    ) -> str:
        if not provider_traces:
            return fallback_trace_id
        last_trace = provider_traces[-1]
        trace_id = getattr(last_trace, "trace_id", "")
        if isinstance(trace_id, str) and trace_id.strip():
            return trace_id
        return fallback_trace_id

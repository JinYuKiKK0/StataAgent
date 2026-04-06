from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar, cast
from uuid import uuid4

from stata_agent.providers.csmar.errors import CsmarMetadataError
from stata_agent.providers.csmar.types import CsmarToolTrace
from stata_agent.services.mapping.contracts import CsmarFieldProbeRequest
from stata_agent.services.mapping.contracts import CsmarFieldProbeResult
from stata_agent.services.mapping.contracts import CsmarTableRecord
from stata_agent.services.mapping.contracts import CsmarTableSchema
from stata_agent.services.mapping.contracts import VariableMappingBudget
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.mapping.ports import MappingProviderScopePort

_ResultT = TypeVar("_ResultT")


class NodeScopedCsmarProvider:
    def __init__(
        self,
        *,
        metadata_provider: CsmarMetadataProviderPort,
        node_name: str,
        allowed_tools: set[str],
        budget: VariableMappingBudget,
    ) -> None:
        self._metadata_provider = metadata_provider
        self._node_name = node_name
        self._allowed_tools = set(allowed_tools)
        self._budget = budget
        self._total_calls = 0
        self._tool_calls: dict[str, int] = {}
        self._local_traces: list[CsmarToolTrace] = []
        self._last_trace_id = ""

    @property
    def last_trace_id(self) -> str:
        return self._last_trace_id

    def list_databases(self) -> list[str]:
        return self._call(
            tool_name="csmar_list_databases",
            request_payload={},
            limit=self._budget.list_databases_limit,
            delegate=self._metadata_provider.list_databases,
        )

    def list_tables(self, database_name: str) -> list[CsmarTableRecord]:
        return self._call(
            tool_name="csmar_list_tables",
            request_payload={"database_name": database_name},
            limit=self._budget.list_tables_limit,
            delegate=lambda: self._metadata_provider.list_tables(database_name),
        )

    def get_table_schema(self, table_code: str) -> CsmarTableSchema:
        return self._call(
            tool_name="csmar_get_table_schema",
            request_payload={"table_code": table_code},
            limit=self._budget.schema_reads_limit,
            delegate=lambda: self._metadata_provider.get_table_schema(table_code),
        )

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        return self._call(
            tool_name="csmar_probe_query",
            request_payload=request.model_dump(mode="json"),
            limit=None,
            delegate=lambda: self._metadata_provider.probe_field_availability(request),
        )

    def drain_tool_traces(self) -> list[CsmarToolTrace]:
        traces = list(self._local_traces)
        self._local_traces.clear()
        return traces

    def _call(
        self,
        *,
        tool_name: str,
        request_payload: dict[str, object],
        limit: int | None,
        delegate: Callable[[], _ResultT],
    ) -> _ResultT:
        self._ensure_tool_allowed(tool_name, request_payload)
        self._ensure_budget(tool_name, request_payload, limit)
        self._total_calls += 1
        self._tool_calls[tool_name] = self._tool_calls.get(tool_name, 0) + 1
        try:
            result = delegate()
        except Exception:
            self._capture_delegate_traces()
            raise
        self._capture_delegate_traces()
        return result

    def _ensure_tool_allowed(
        self,
        tool_name: str,
        request_payload: dict[str, object],
    ) -> None:
        if tool_name in self._allowed_tools:
            return
        self._record_local_error(
            tool_name=tool_name,
            request_payload=request_payload,
            code="tool_not_allowed",
            message=f"节点 `{self._node_name}` 不允许调用 {tool_name}。",
            hint="请切换到该节点白名单内的工具。",
        )
        raise CsmarMetadataError(
            f"节点 `{self._node_name}` 不允许调用 {tool_name}。",
            code="tool_not_allowed",
            hint="请切换到该节点白名单内的工具。",
        )

    def _ensure_budget(
        self,
        tool_name: str,
        request_payload: dict[str, object],
        limit: int | None,
    ) -> None:
        if self._total_calls >= self._budget.max_total_calls:
            self._raise_budget_exhausted(tool_name, request_payload)
        if limit is None:
            return
        if self._tool_calls.get(tool_name, 0) >= limit:
            self._raise_budget_exhausted(tool_name, request_payload)

    def _raise_budget_exhausted(
        self,
        tool_name: str,
        request_payload: dict[str, object],
    ) -> None:
        message = f"节点 `{self._node_name}` 的 {tool_name} 调用预算已耗尽。"
        self._record_local_error(
            tool_name=tool_name,
            request_payload=request_payload,
            code="budget_exhausted",
            message=message,
            hint="停止继续查询，并输出当前已确认与未确认的映射结果。",
        )
        raise CsmarMetadataError(
            message,
            code="budget_exhausted",
            hint="停止继续查询，并输出当前已确认与未确认的映射结果。",
        )

    def _capture_delegate_traces(self) -> None:
        drain = getattr(self._metadata_provider, "drain_tool_traces", None)
        if not callable(drain):
            return
        raw_traces = drain()
        if not isinstance(raw_traces, list):
            return
        trace_items = cast(list[object], raw_traces)
        traces: list[CsmarToolTrace] = []
        for item in trace_items:
            if isinstance(item, CsmarToolTrace):
                traces.append(item)
                continue
            try:
                traces.append(CsmarToolTrace.model_validate(item))
            except Exception:
                continue
        if traces:
            self._last_trace_id = traces[-1].trace_id
            self._local_traces.extend(traces)

    def _record_local_error(
        self,
        *,
        tool_name: str,
        request_payload: dict[str, object],
        code: str,
        message: str,
        hint: str,
    ) -> None:
        trace_id = f"trace_{uuid4().hex[:10]}"
        started_at = datetime.now(timezone.utc).isoformat()
        trace = CsmarToolTrace(
            trace_id=trace_id,
            tool_name=tool_name,
            request_payload=request_payload,
            result_summary=None,
            error={"code": code, "message": message, "hint": hint},
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._last_trace_id = trace_id
        self._local_traces.append(trace)


class NodeScopedCsmarProviderFactory(MappingProviderScopePort):
    def create_mapping_provider(
        self,
        metadata_provider: CsmarMetadataProviderPort,
        budget: VariableMappingBudget,
    ) -> NodeScopedCsmarProvider:
        return NodeScopedCsmarProvider(
            metadata_provider=metadata_provider,
            node_name="map_variables",
            allowed_tools={
                "csmar_list_databases",
                "csmar_list_tables",
                "csmar_get_table_schema",
            },
            budget=budget,
        )

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from stata_agent.domains.mapping.types import CsmarToolTrace
from stata_agent.providers.csmar.contracts import McpToolPayload
from stata_agent.providers.csmar.errors import CsmarMetadataError
from stata_agent.providers.csmar.mcp_transport import CsmarMcpToolCaller


def call_mcp_tool_with_trace(
    *,
    tool_name: str,
    arguments: dict[str, object],
    caller: CsmarMcpToolCaller,
    tool_traces: list[CsmarToolTrace],
) -> McpToolPayload:
    trace_id = f"trace_{uuid4().hex[:10]}"
    started_at = datetime.now(timezone.utc).isoformat()

    payload: McpToolPayload | None = None
    captured_error: CsmarMetadataError | None = None
    error_payload: dict[str, object] | None = None

    try:
        payload = caller.call_tool(tool_name, arguments)
    except CsmarMetadataError as error:
        captured_error = error
        error_payload = {
            "code": error.code,
            "message": str(error),
            "hint": error.hint,
            "retry_after_seconds": error.retry_after_seconds,
            "suggested_args_patch": error.suggested_args_patch,
        }
    except Exception as error:
        message = str(error).strip() or "MCP tool 调用失败。"
        captured_error = CsmarMetadataError(
            message,
            code="upstream_error",
            retriable=True,
            vendor_message=message,
            hint="请稍后重试；若持续失败，请检查 MCP 服务日志。",
        )
        error_payload = {
            "code": captured_error.code,
            "message": str(captured_error),
            "hint": captured_error.hint,
            "retry_after_seconds": captured_error.retry_after_seconds,
            "suggested_args_patch": captured_error.suggested_args_patch,
        }

    content = payload.content if payload is not None else {}
    query_fingerprint = str(content.get("query_fingerprint") or "").strip() or None
    validation_id = (
        str(content.get("validation_id") or arguments.get("validation_id") or "").strip()
        or None
    )
    tool_traces.append(
        CsmarToolTrace(
            trace_id=trace_id,
            tool_name=tool_name,
            request_payload=arguments,
            result_summary={"keys": sorted(content.keys())} if content else None,
            error=error_payload,
            query_fingerprint=query_fingerprint,
            validation_id=validation_id,
            cached=False,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    )

    if payload is None and captured_error is not None:
        raise captured_error
    if payload is None:
        raise CsmarMetadataError("MCP tool 调用失败。", code="upstream_error")
    return payload
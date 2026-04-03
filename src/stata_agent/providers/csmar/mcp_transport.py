# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, cast

from stata_agent.providers.csmar.contracts import McpToolPayload
from stata_agent.providers.csmar.errors import CsmarMetadataError
from stata_agent.providers.csmar.mcp_runtime import CsmarMcpLaunchSpec


class CsmarMcpToolCaller(Protocol):
    def call_tool(self, tool_name: str, arguments: dict[str, object]) -> McpToolPayload: ...


@dataclass(frozen=True, slots=True)
class StdioCsmarMcpToolCaller:
    launch_spec: CsmarMcpLaunchSpec

    def call_tool(self, tool_name: str, arguments: dict[str, object]) -> McpToolPayload:
        return asyncio.run(self._call_tool_async(tool_name, arguments))

    async def _call_tool_async(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpToolPayload:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:  # pragma: no cover - 运行时依赖
            raise CsmarMetadataError(
                "未检测到 mcp 客户端依赖，请安装 `mcp` 后重试。",
                code="sdk_missing",
            ) from exc

        launch_env = os.environ.copy()
        launch_env.update(self.launch_spec.env_overrides)
        server_params = StdioServerParameters(
            command=self.launch_spec.command,
            args=list(self.launch_spec.args),
            env=launch_env,
            cwd=str(self.launch_spec.cwd),
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await asyncio.wait_for(
                    session.initialize(),
                    timeout=self.launch_spec.start_timeout_seconds,
                )
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=self.launch_spec.call_timeout_seconds,
                )

        return normalize_tool_result(result)


def normalize_tool_result(result: object) -> McpToolPayload:
    payload = _extract_structured_content(result)
    is_error = _extract_is_error(result)
    if not is_error:
        return payload

    content = payload.content
    code = str(content.get("code") or "upstream_error")
    message = str(content.get("message") or "CSMAR MCP tool call failed")
    hint = str(content.get("hint") or "")
    retry_after_seconds = _to_int(content.get("retry_after_seconds"))
    suggested_args_patch = _to_object_dict(content.get("suggested_args_patch"))

    raise CsmarMetadataError(
        message,
        code=code,
        retriable=code in {"rate_limited", "upstream_error"},
        vendor_message=message,
        hint=hint,
        retry_after_seconds=retry_after_seconds,
        suggested_args_patch=suggested_args_patch,
    )


def _extract_structured_content(result: object) -> McpToolPayload:
    structured_content = getattr(result, "structuredContent", None)
    if structured_content is None:
        structured_content = getattr(result, "structured_content", None)

    if isinstance(structured_content, Mapping):
        return McpToolPayload(content=dict(cast(Mapping[str, object], structured_content)))

    model_dump = getattr(structured_content, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        if isinstance(dumped, Mapping):
            return McpToolPayload(content=dict(cast(Mapping[str, object], dumped)))

    if isinstance(result, Mapping):
        if "structuredContent" in result and isinstance(
            result["structuredContent"], Mapping
        ):
            return McpToolPayload(
                content=dict(cast(Mapping[str, object], result["structuredContent"]))
            )
        if "structured_content" in result and isinstance(
            result["structured_content"], Mapping
        ):
            return McpToolPayload(
                content=dict(cast(Mapping[str, object], result["structured_content"]))
            )

    raise CsmarMetadataError(
        "MCP 工具返回缺少 structuredContent，无法解析。",
        code="upstream_error",
    )


def _extract_is_error(result: object) -> bool:
    attr_value = getattr(result, "isError", None)
    if attr_value is None:
        attr_value = getattr(result, "is_error", None)
    if isinstance(attr_value, bool):
        return attr_value

    if isinstance(result, Mapping):
        mapping = cast(Mapping[str, object], result)
        if isinstance(mapping.get("isError"), bool):
            return bool(mapping["isError"])
        if isinstance(mapping.get("is_error"), bool):
            return bool(mapping["is_error"])

    return False


def _to_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _to_object_dict(value: object) -> dict[str, object] | None:
    if isinstance(value, Mapping):
        return dict(cast(Mapping[str, object], value))
    return None

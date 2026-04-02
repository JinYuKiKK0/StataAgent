from __future__ import annotations

import importlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from secrets import token_hex
from typing import cast

from stata_agent.domains.fetch.types import QueryPlan
from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import CsmarFieldProbeRequest
from stata_agent.domains.mapping.types import CsmarFieldProbeResult
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest
from stata_agent.providers.csmar.catalog import CatalogRow
from stata_agent.providers.csmar.catalog import normalize_database_names
from stata_agent.providers.csmar.catalog import normalize_fields
from stata_agent.providers.csmar.catalog import normalize_tables
from stata_agent.providers.csmar.catalog import score_candidate
from stata_agent.providers.csmar.errors import CsmarMetadataError


class CsmarBridgeClient:
    def __init__(
        self,
        *,
        account: str | None = None,
        password: str | None = None,
        language: int = 0,
    ) -> None:
        self._account = (account or "").strip()
        self._password = (password or "").strip()
        self._language = language
        self._service: object | None = None
        self._catalog_rows: tuple[CatalogRow, ...] | None = None

    def fetch(self, plan: QueryPlan, output_dir: Path) -> Path:
        return output_dir / f"{plan.table_name}.parquet"

    def search_field_candidates(
        self, request: CsmarFieldSearchRequest
    ) -> list[CsmarFieldCandidate]:
        variable_name = request.variable_name.strip()
        if not variable_name:
            raise CsmarMetadataError(
                "变量名为空，无法检索 CSMAR 字段候选。", code="invalid_request"
            )

        scored: list[tuple[int, CsmarFieldCandidate]] = []
        for row in self._load_catalog_rows():
            score, candidate = score_candidate(row, request)
            if score > 0:
                scored.append(
                    (score, candidate.model_copy(update={"variable_name": variable_name}))
                )
        ranked = [
            item for _, item in sorted(scored, key=lambda item: item[0], reverse=True)
        ]
        return ranked[: max(1, request.candidate_limit)]

    def probe_field_availability(
        self, request: CsmarFieldProbeRequest
    ) -> CsmarFieldProbeResult:
        query_fingerprint = (
            f"{request.table_name}.{request.field_name}:"
            f"{request.time_start_year}-{request.time_end_year}"
        )
        row = self._find_catalog_row(request.table_name, request.field_name)
        if row is None:
            return CsmarFieldProbeResult(
                variable_name=request.variable_name,
                table_name=request.table_name,
                field_name=request.field_name,
                field_exists=False,
                query_fingerprint=query_fingerprint,
                scope_level="time_scoped",
                vendor_message="字段未出现在当前 catalog 中。",
            )

        try:
            payload = self._call_service(
                "queryCount",
                [request.field_name],
                _build_query_condition(request.field_name),
                request.table_name,
                f"{request.time_start_year}-01-01",
                f"{request.time_end_year}-12-31",
            )
        except CsmarMetadataError as exc:
            return CsmarFieldProbeResult(
                variable_name=request.variable_name,
                table_name=request.table_name,
                field_name=request.field_name,
                field_exists=True,
                query_fingerprint=query_fingerprint,
                scope_level="time_scoped",
                vendor_message=exc.vendor_message,
                retriable=exc.retriable,
                frequency_tags=list(row.frequency_tags),
                warnings=_probe_scope_warnings(request.entity_scope),
            )

        count = _extract_first_int(payload)
        if count is None:
            raise CsmarMetadataError(
                f"queryCount 返回无法解析：{request.table_name}.{request.field_name}: {payload!r}",
                code="probe_failed",
            )
        return CsmarFieldProbeResult(
            variable_name=request.variable_name,
            table_name=request.table_name,
            field_name=request.field_name,
            field_exists=True,
            row_count=count,
            query_fingerprint=query_fingerprint,
            scope_level="time_scoped",
            frequency_tags=list(row.frequency_tags),
            warnings=_probe_scope_warnings(request.entity_scope),
        )

    def _load_catalog_rows(self) -> tuple[CatalogRow, ...]:
        if self._catalog_rows is not None:
            return self._catalog_rows

        rows: list[CatalogRow] = []
        for database_name in normalize_database_names(self._call_service("getListDbs")):
            tables = normalize_tables(self._call_service("getListTables", database_name))
            for table_name, table_label in tables:
                rows.extend(
                    normalize_fields(
                        payload=self._call_service("getListFields", table_name),
                        database_name=database_name,
                        table_name=table_name,
                        table_label=table_label,
                    )
                )
        self._catalog_rows = tuple(rows)
        return self._catalog_rows

    def _find_catalog_row(self, table_name: str, field_name: str) -> CatalogRow | None:
        for row in self._load_catalog_rows():
            if row.table_name == table_name and row.field_name == field_name:
                return row
        return None

    def _call_service(self, method_name: str, *args: object) -> object:
        service = self._ensure_service()
        method = getattr(service, method_name, None)
        if not callable(method):
            raise CsmarMetadataError(
                f"CSMAR SDK 缺少方法：{method_name}", code="missing_method"
            )
        try:
            return method(*args)
        except Exception as exc:  # pragma: no cover - 依赖上游 SDK
            message = str(exc)
            if "30分钟" in message or "30 分钟" in message:
                raise CsmarMetadataError(
                    f"CSMAR 探针命中冷却限制：{message}",
                    code="cooldown_limited",
                    retriable=True,
                    vendor_message=message,
                ) from exc
            raise CsmarMetadataError(
                f"CSMAR 调用失败：{method_name}: {message}",
                code="probe_failed",
                vendor_message=message,
            ) from exc

    def _ensure_service(self) -> object:
        if self._service is not None:
            return self._service
        if not self._account or not self._password:
            raise CsmarMetadataError(
                "CSMAR 凭证缺失：请配置 CSMAR_ACCOUNT 与 CSMAR_PASSWORD。",
                code="auth",
            )
        try:
            module = importlib.import_module("csmarapi.CsmarService")
        except ImportError as exc:
            raise CsmarMetadataError(
                "未检测到 csmarapi SDK，请先按 CSMAR 官方说明完成安装。",
                code="sdk_missing",
            ) from exc
        service_factory = getattr(module, "CsmarService", None)
        if not callable(service_factory):
            raise CsmarMetadataError(
                "csmarapi.CsmarService.CsmarService 不可用。",
                code="sdk_missing",
            )

        service = service_factory()
        login = getattr(service, "login", None)
        if not callable(login):
            raise CsmarMetadataError("CSMAR SDK 缺少 login 方法。", code="missing_method")
        try:
            login(self._account, self._password, str(self._language))
        except Exception as exc:  # pragma: no cover - 依赖上游 SDK
            raise CsmarMetadataError(
                f"CSMAR 登录失败：{exc}",
                code="auth",
                vendor_message=str(exc),
            ) from exc
        self._service = service
        return service


def _probe_scope_warnings(entity_scope: str) -> list[str]:
    if not entity_scope.strip():
        return []
    return ["当前 probe 已按时间范围缩限，样本范围仍待后续主键与筛选规则验证。"]


def _build_query_condition(field_name: str) -> str:
    nonce = token_hex(4)
    return f"{field_name} is not null and '{nonce}'='{nonce}'"


def _extract_first_int(payload: object) -> int | None:
    if isinstance(payload, bool):
        return None
    if isinstance(payload, int):
        return payload
    if isinstance(payload, float):
        return int(payload)
    if isinstance(payload, str):
        matched = re.search(r"-?\d+", payload)
        return None if matched is None else int(matched.group())
    if isinstance(payload, Mapping):
        for value in cast(Mapping[object, object], payload).values():
            parsed = _extract_first_int(value)
            if parsed is not None:
                return parsed
        return None
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for value in cast(Sequence[object], payload):
            parsed = _extract_first_int(value)
            if parsed is not None:
                return parsed
    return None

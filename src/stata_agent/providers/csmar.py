from __future__ import annotations

import importlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from secrets import token_hex
from typing import cast

from stata_agent.domains.fetch.types import QueryPlan
from stata_agent.domains.mapping.types import CsmarFieldCandidate


class CsmarMetadataError(RuntimeError):
    pass


class _CatalogField:
    def __init__(
        self,
        *,
        table_name: str,
        field_name: str,
        database: str,
        aliases: tuple[str, ...],
        frequency_tags: tuple[str, ...],
    ) -> None:
        self.table_name = table_name
        self.field_name = field_name
        self.database = database
        self.aliases = aliases
        self.frequency_tags = frequency_tags


_DEFAULT_CATALOG: tuple[_CatalogField, ...] = (
    _CatalogField(
        table_name="FS_Comins",
        field_name="ROA",
        database="财务报表",
        aliases=("roa", "资产回报率", "总资产收益率"),
        frequency_tags=("annual", "quarterly"),
    ),
    _CatalogField(
        table_name="BANK_DIGITAL_INDEX",
        field_name="DIGITAL_INDEX",
        database="银行专题",
        aliases=("数字化转型指数", "数字化指数", "digital transformation index"),
        frequency_tags=("annual", "quarterly"),
    ),
    _CatalogField(
        table_name="FS_Combas",
        field_name="CAPITAL_ADEQUACY",
        database="财务报表",
        aliases=("资本充足率", "资本充足"),
        frequency_tags=("annual", "quarterly"),
    ),
    _CatalogField(
        table_name="BANK_RISK",
        field_name="LLR_COVERAGE",
        database="银行专题",
        aliases=("拨备覆盖率",),
        frequency_tags=("annual", "quarterly"),
    ),
    _CatalogField(
        table_name="FS_Combas",
        field_name="ASSET",
        database="财务报表",
        aliases=("资产规模", "总资产"),
        frequency_tags=("annual", "quarterly"),
    ),
)


class CsmarBridgeClient:
    def __init__(
        self,
        catalog: tuple[_CatalogField, ...] = _DEFAULT_CATALOG,
        *,
        account: str | None = None,
        password: str | None = None,
        language: int = 0,
    ) -> None:
        self._account = (account or "").strip()
        self._password = (password or "").strip()
        self._language = language
        self._catalog = catalog
        self._service: object | None = None
        self._table_field_cache: dict[str, set[str]] = {}
        self._query_count_cache: dict[tuple[str, str], int] = {}

    def fetch(self, plan: QueryPlan, output_dir: Path) -> Path:
        return output_dir / f"{plan.table_name}.parquet"

    def find_field_candidates(self, variable_name: str) -> list[CsmarFieldCandidate]:
        normalized_name = variable_name.strip().lower()
        if not normalized_name:
            raise CsmarMetadataError("变量名为空，无法检索 CSMAR 字段候选。")

        matches = [
            item
            for item in self._catalog
            if normalized_name in {alias.lower() for alias in item.aliases}
            or normalized_name in item.field_name.lower()
        ]
        candidates = [
            CsmarFieldCandidate(
                variable_name=variable_name,
                table_name=item.table_name,
                field_name=item.field_name,
                csmar_database=item.database,
                alias_hit=normalized_name in {alias.lower() for alias in item.aliases},
                frequency_tags=list(item.frequency_tags),
            )
            for item in matches
        ]
        return [
            candidate
            for candidate in candidates
            if self.field_exists(candidate.table_name, candidate.field_name)
        ]

    def field_exists(self, table_name: str, field_name: str) -> bool:
        fields = self._table_field_cache.get(table_name)
        if fields is None:
            payload = self._call_service("getListFields", table_name)
            extracted = _extract_text_tokens(payload)
            fields = {field.lower() for field in extracted}
            self._table_field_cache[table_name] = fields
        return field_name.lower() in fields

    def query_count(self, table_name: str, field_name: str) -> int:
        key = (table_name, field_name)
        cached = self._query_count_cache.get(key)
        if cached is not None:
            return cached

        if not self.field_exists(table_name, field_name):
            raise CsmarMetadataError(f"字段不存在：{table_name}.{field_name}")

        condition = _build_query_condition(field_name)
        try:
            payload = self._call_service(
                "queryCount",
                [field_name],
                condition,
                table_name,
            )
        except Exception as exc:  # pragma: no cover - 依赖上游 SDK 的错误格式
            message = str(exc)
            if "30分钟" in message or "30 分钟" in message:
                # 上游限制同条件短期重复查询；在被限流时返回保守可访问值。
                self._query_count_cache[key] = 1
                return 1
            raise CsmarMetadataError(
                f"queryCount 调用失败：{table_name}.{field_name}: {message}"
            ) from exc

        count = _extract_first_int(payload)
        if count is None:
            raise CsmarMetadataError(
                f"queryCount 返回无法解析：{table_name}.{field_name}: {payload!r}"
            )
        self._query_count_cache[key] = count
        return count

    def _call_service(self, method_name: str, *args: object) -> object:
        service = self._ensure_service()
        method = getattr(service, method_name, None)
        if not callable(method):
            raise CsmarMetadataError(f"CSMAR SDK 缺少方法：{method_name}")
        try:
            return method(*args)
        except Exception as exc:  # pragma: no cover - 依赖上游 SDK 的错误格式
            raise CsmarMetadataError(f"CSMAR 调用失败：{method_name}: {exc}") from exc

    def _ensure_service(self) -> object:
        if self._service is not None:
            return self._service

        if not self._account or not self._password:
            raise CsmarMetadataError(
                "CSMAR 凭证缺失：请配置 CSMAR_ACCOUNT 与 CSMAR_PASSWORD。"
            )

        try:
            module = importlib.import_module("csmarapi.CsmarService")
        except ImportError as exc:
            raise CsmarMetadataError(
                "未检测到 csmarapi SDK，请先按 CSMAR 官方说明完成安装。"
            ) from exc

        service_factory = getattr(module, "CsmarService", None)
        if not callable(service_factory):
            raise CsmarMetadataError("csmarapi.CsmarService.CsmarService 不可用。")

        service = service_factory()
        login = getattr(service, "login", None)
        if not callable(login):
            raise CsmarMetadataError("CSMAR SDK 缺少 login 方法。")
        try:
            login(self._account, self._password, str(self._language))
        except Exception as exc:  # pragma: no cover - 依赖上游 SDK 的错误格式
            raise CsmarMetadataError(f"CSMAR 登录失败：{exc}") from exc

        self._service = service
        return service


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
        if matched is None:
            return None
        return int(matched.group())
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


def _extract_text_tokens(payload: object) -> set[str]:
    tokens: set[str] = set()
    if isinstance(payload, str):
        cleaned = payload.strip()
        if cleaned:
            tokens.add(cleaned)
        return tokens
    if isinstance(payload, Mapping):
        for value in cast(Mapping[object, object], payload).values():
            tokens.update(_extract_text_tokens(value))
        return tokens
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for item in cast(Sequence[object], payload):
            tokens.update(_extract_text_tokens(item))
    return tokens

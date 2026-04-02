from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from stata_agent.domains.mapping.types import CsmarFieldCandidate
from stata_agent.domains.mapping.types import CsmarFieldSearchRequest

_ALIAS_HINTS: dict[str, tuple[str, ...]] = {
    "ROA": ("roa", "资产回报率", "总资产收益率"),
    "DIGITAL_INDEX": ("数字化转型指数", "数字化指数", "digital transformation index"),
    "CAPITAL_ADEQUACY": ("资本充足率", "资本充足"),
    "LLR_COVERAGE": ("拨备覆盖率",),
    "ASSET": ("资产规模", "总资产", "资产总计"),
}

_FREQUENCY_HINTS: dict[str, tuple[str, ...]] = {
    "ROA": ("annual", "quarterly"),
    "DIGITAL_INDEX": ("annual", "quarterly"),
    "CAPITAL_ADEQUACY": ("annual", "quarterly"),
    "LLR_COVERAGE": ("annual", "quarterly"),
    "ASSET": ("annual", "quarterly"),
}


@dataclass(frozen=True)
class CatalogRow:
    database_name: str
    table_name: str
    table_label: str
    field_name: str
    field_label: str
    field_description: str
    aliases: tuple[str, ...]
    frequency_tags: tuple[str, ...]


def score_candidate(
    row: CatalogRow, request: CsmarFieldSearchRequest
) -> tuple[int, CsmarFieldCandidate]:
    score = 0
    evidence: list[str] = []
    variable_name = _normalize_text(request.variable_name)
    haystacks = {
        "field_name": _normalize_text(row.field_name),
        "field_label": _normalize_text(row.field_label),
        "table_label": _normalize_text(row.table_label),
        "database": _normalize_text(row.database_name),
    }
    alias_hit = False
    for alias in row.aliases:
        normalized_alias = _normalize_text(alias)
        if not normalized_alias:
            continue
        if variable_name == normalized_alias:
            score += 8
            alias_hit = True
            evidence.append(f"alias精确命中={alias}")
        elif variable_name in normalized_alias or normalized_alias in variable_name:
            score += 5
            evidence.append(f"alias语义接近={alias}")
    if variable_name and variable_name in haystacks["field_label"]:
        score += 6
        evidence.append("字段标签包含变量名")
    if variable_name and variable_name in haystacks["field_name"]:
        score += 4
        evidence.append("字段代码包含变量名")
    if any("bank" in grain.lower() for grain in request.analysis_grain_candidates):
        if "银行" in haystacks["database"] or "银行" in haystacks["table_label"]:
            score += 2
            evidence.append("分析粒度与银行域一致")
    if any("year" in grain.lower() for grain in request.analysis_grain_candidates):
        if "annual" in row.frequency_tags:
            score += 1
            evidence.append("年频候选")
    if any("quarter" in grain.lower() for grain in request.analysis_grain_candidates):
        if "quarterly" in row.frequency_tags:
            score += 1
            evidence.append("季频候选")
    if request.entity_scope and "银行" in request.entity_scope:
        if "银行" in haystacks["database"] or "银行" in haystacks["table_label"]:
            score += 2
            evidence.append("样本范围与银行域一致")
    if request.topic and "数字化" in request.topic and "digital" in haystacks["field_name"]:
        score += 1
        evidence.append("主题与字段代码语义接近")
    return score, CsmarFieldCandidate(
        variable_name=request.variable_name,
        table_name=row.table_name,
        field_name=row.field_name,
        csmar_database=row.database_name,
        alias_hit=alias_hit,
        table_label=row.table_label,
        field_label=row.field_label,
        field_description=row.field_description,
        aliases=list(row.aliases),
        match_evidence=_dedupe_strings(evidence),
        frequency_tags=list(row.frequency_tags),
        catalog_source="sdk_catalog",
    )


def normalize_database_names(payload: object) -> list[str]:
    names: list[str] = []
    for item in _as_sequence(payload):
        text = _pick_first_text(item, ("dbName", "databaseName", "name", "label"))
        if text is None and isinstance(item, str):
            text = item
        if text:
            names.append(text)
    return _dedupe_strings(names)


def normalize_tables(payload: object) -> list[tuple[str, str]]:
    tables: list[tuple[str, str]] = []
    for item in _as_sequence(payload):
        if isinstance(item, str):
            tables.append((item, item))
            continue
        table_name = _pick_first_text(
            item, ("tableName", "tableCode", "table", "name", "code")
        )
        table_label = _pick_first_text(item, ("tableLabel", "label", "cnName", "chName"))
        if table_name is not None:
            tables.append((table_name, table_label or table_name))
    return tables


def normalize_fields(
    *,
    payload: object,
    database_name: str,
    table_name: str,
    table_label: str,
) -> list[CatalogRow]:
    rows: list[CatalogRow] = []
    for item in _as_sequence(payload):
        if isinstance(item, str):
            field_name = item
            field_label = ""
            field_description = ""
            aliases = _ALIAS_HINTS.get(field_name.upper(), ())
        else:
            mapping = cast(Mapping[object, object], item)
            field_name = _pick_first_text(
                mapping, ("field", "fieldName", "column", "code", "name")
            )
            if field_name is None:
                continue
            field_label = _pick_first_text(
                mapping, ("fieldLabel", "label", "cnName", "chName", "displayName")
            ) or ""
            field_description = _pick_first_text(
                mapping, ("description", "desc", "remark", "memo")
            ) or ""
            dynamic_aliases = _collect_texts(mapping.get("alias"))
            aliases = tuple(
                _dedupe_strings([*dynamic_aliases, *_ALIAS_HINTS.get(field_name.upper(), ())])
            )
        rows.append(
            CatalogRow(
                database_name=database_name,
                table_name=table_name,
                table_label=table_label,
                field_name=field_name,
                field_label=field_label,
                field_description=field_description,
                aliases=aliases,
                frequency_tags=_FREQUENCY_HINTS.get(field_name.upper(), ()),
            )
        )
    return rows


def _as_sequence(payload: object) -> list[object]:
    if isinstance(payload, Mapping):
        nested = cast(Mapping[object, object], payload).get("data")
        if nested is not None:
            return _as_sequence(nested)
        return list(cast(Mapping[object, object], payload).values())
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return list(cast(Sequence[object], payload))
    return [payload]


def _pick_first_text(item: object, keys: Iterable[str]) -> str | None:
    if not isinstance(item, Mapping):
        return None
    mapping = cast(Mapping[object, object], item)
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _collect_texts(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        texts: list[str] = []
        for item in cast(Sequence[object], value):
            texts.extend(_collect_texts(item))
        return texts
    return []


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            deduped.append(cleaned)
            seen.add(cleaned)
    return deduped

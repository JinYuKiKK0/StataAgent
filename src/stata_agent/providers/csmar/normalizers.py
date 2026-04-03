from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import cast


def probe_scope_warnings(entity_scope: str) -> list[str]:
    if not entity_scope.strip():
        return []
    return ["当前 probe 已按时间范围缩限，样本范围仍待后续主键与筛选规则验证。"]


def normalize_tags(value: object) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        tags: list[str] = []
        for item in cast(Sequence[object], value):
            tags.extend(normalize_tags(item))
        deduped: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            if tag not in seen:
                deduped.append(tag)
                seen.add(tag)
        return deduped
    return []


def normalize_object_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, object]] = []
    for item in cast(Sequence[object], value):
        if isinstance(item, Mapping):
            rows.append(dict(cast(Mapping[str, object], item)))
    return rows


def build_query_condition(field_name: str) -> str:
    return f"{field_name} is not null"


def extract_first_int(payload: object) -> int | None:
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
            parsed = extract_first_int(value)
            if parsed is not None:
                return parsed
        return None
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for value in cast(Sequence[object], payload):
            parsed = extract_first_int(value)
            if parsed is not None:
                return parsed
    return None

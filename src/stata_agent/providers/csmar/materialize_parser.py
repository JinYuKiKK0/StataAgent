from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from stata_agent.providers.csmar.errors import CsmarMetadataError
from stata_agent.providers.csmar.normalizers import extract_first_int, normalize_tags
from stata_agent.providers.csmar.types import CsmarMaterializeAudit
from stata_agent.providers.csmar.types import CsmarMaterializeQueryResult


def parse_materialize_payload(payload: Mapping[str, object]) -> CsmarMaterializeQueryResult:
    required_keys = {
        "download_id",
        "query_fingerprint",
        "output_dir",
        "files",
        "row_count",
        "archive_path",
        "audit",
    }
    missing_keys = sorted(required_keys.difference(payload.keys()))
    if missing_keys:
        raise CsmarMetadataError(
            f"MCP materialize 返回缺少关键字段。缺失: {', '.join(missing_keys)}",
            code="upstream_error",
        )

    download_id = str(payload.get("download_id") or "").strip()
    query_fingerprint = str(payload.get("query_fingerprint") or "").strip()
    resolved_output_dir = str(payload.get("output_dir") or "").strip()
    archive_path = str(payload.get("archive_path") or "").strip()
    row_count = extract_first_int(payload.get("row_count"))
    audit_obj = payload.get("audit")
    typed_audit_obj = (
        cast(Mapping[str, object], audit_obj)
        if isinstance(audit_obj, Mapping)
        else None
    )
    if (
        not download_id
        or not query_fingerprint
        or not resolved_output_dir
        or not archive_path
        or row_count is None
        or typed_audit_obj is None
    ):
        raise CsmarMetadataError("MCP materialize 返回关键字段格式非法。", code="upstream_error")

    retries = extract_first_int(typed_audit_obj.get("retries"))
    packaged_at = str(typed_audit_obj.get("packaged_at") or "").strip()
    completed_at = str(typed_audit_obj.get("completed_at") or "").strip()
    if retries is None or not packaged_at or not completed_at:
        raise CsmarMetadataError("MCP materialize 返回 audit 字段格式非法。", code="upstream_error")

    return CsmarMaterializeQueryResult(
        download_id=download_id,
        query_fingerprint=query_fingerprint,
        output_dir=resolved_output_dir,
        files=[str(item) for item in normalize_tags(payload.get("files"))],
        row_count=row_count,
        archive_path=archive_path,
        audit=CsmarMaterializeAudit(
            retries=retries,
            packaged_at=packaged_at,
            completed_at=completed_at,
        ),
    )

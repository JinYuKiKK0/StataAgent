from __future__ import annotations

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.ports import ResearchSpecGenerator
from stata_agent.domains.spec.types import RequirementParseResult, ResearchSpec


class RequirementParser:
    def __init__(self, generator: ResearchSpecGenerator) -> None:
        self._generator = generator

    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        result = self._generator.parse_request(request)
        if result.spec is None:
            return self._failure_result(
                result,
                "需求解析失败：Tongyi 未产出可用的研究规范。",
            )

        expected_start_year, expected_end_year = _parse_time_range(request.time_range)
        validation_error = _validate_spec_against_request(
            request=request,
            spec=result.spec,
            expected_start_year=expected_start_year,
            expected_end_year=expected_end_year,
        )
        if validation_error is not None:
            return self._failure_result(result, validation_error)

        normalized_spec = result.spec.model_copy(
            update={
                "topic": result.spec.topic.strip(),
                "dependent_variable": request.dependent_variable,
                "independent_variables": [
                    variable.strip() for variable in request.independent_variables
                ],
                "entity_scope": (
                    request.entity_scope.strip()
                    if request.entity_scope
                    else result.spec.entity_scope.strip()
                ),
                "entity_scope_inferred": request.entity_scope is None,
                "time_start_year": expected_start_year,
                "time_end_year": expected_end_year,
                "analysis_frequency_hint": _normalize_frequency_hint(
                    result.spec.analysis_frequency_hint
                ),
                "control_variable_candidates": _normalize_candidates(
                    result.spec.control_variable_candidates
                ),
                "analysis_grain_candidates": _normalize_candidates(
                    result.spec.analysis_grain_candidates
                ),
            }
        )
        return result.model_copy(update={"spec": normalized_spec})

    def _failure_result(
        self, result: RequirementParseResult, reason: str
    ) -> RequirementParseResult:
        warnings = list(result.warnings)
        if reason not in warnings:
            warnings.append(reason)
        return result.model_copy(
            update={
                "spec": None,
                "failure_reason": reason,
                "warnings": warnings,
            }
        )


def _parse_time_range(time_range: str) -> tuple[int, int]:
    start_year_text, end_year_text = time_range.split("-", maxsplit=1)
    return int(start_year_text), int(end_year_text)


def _validate_spec_against_request(
    *,
    request: ResearchRequest,
    spec: ResearchSpec,
    expected_start_year: int,
    expected_end_year: int,
) -> str | None:
    if spec.dependent_variable.strip() != request.dependent_variable.strip():
        return "需求解析失败：模型改写了用户给定的因变量。"
    if [value.strip() for value in spec.independent_variables] != [
        value.strip() for value in request.independent_variables
    ]:
        return "需求解析失败：模型改写了用户给定的自变量。"
    if request.entity_scope is not None:
        if spec.entity_scope.strip() != request.entity_scope.strip():
            return "需求解析失败：模型改写了用户给定的样本范围。"
    if (
        spec.time_start_year != expected_start_year
        or spec.time_end_year != expected_end_year
    ):
        return "需求解析失败：模型改写了用户给定的时间范围。"
    if not spec.analysis_grain_candidates:
        return "需求解析失败：模型没有提供候选分析粒度。"

    forbidden_controls = {request.dependent_variable, *request.independent_variables}
    overlapping_controls = [
        candidate
        for candidate in spec.control_variable_candidates
        if candidate in forbidden_controls
    ]
    if overlapping_controls:
        return "需求解析失败：控制变量候选与用户指定的核心变量重复。"
    return None


def _normalize_candidates(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
    return normalized


def _normalize_frequency_hint(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"annual", "quarterly", "monthly", "unknown"}:
        return normalized
    return "unknown"

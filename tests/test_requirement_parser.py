from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import RequirementParseResult, ResearchSpec
from stata_agent.services.requirement_parser import RequirementParser


class SuccessfulGenerator:
    def parse_request(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(
            spec=ResearchSpec(
                topic="银行数字化转型与风险承担研究",
                dependent_variable=request.dependent_variable,
                independent_variables=request.independent_variables,
                entity_scope=request.entity_scope,
                time_start_year=2010,
                time_end_year=2023,
                control_variable_candidates=["资产规模", "资本充足率"],
                analysis_grain_candidates=["bank-year"],
            ),
            raw_response_text="structured output",
            warnings=["题目中的数字化口径需后续映射确认"],
        )


class ConflictingGenerator:
    def parse_request(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(
            spec=ResearchSpec(
                topic=request.topic,
                dependent_variable="NPL",
                independent_variables=request.independent_variables,
                entity_scope=request.entity_scope,
                time_start_year=2010,
                time_end_year=2023,
                control_variable_candidates=["ROA"],
                analysis_grain_candidates=["bank-year"],
            ),
            raw_response_text="invalid output",
        )


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_range="2010-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def test_requirement_parser_returns_validated_spec() -> None:
    parser = RequirementParser(generator=SuccessfulGenerator())

    result = parser.parse(_build_request())

    assert result.failure_reason is None
    assert result.spec is not None
    assert result.spec.analysis_grain_candidates == ["bank-year"]
    assert result.spec.control_variable_candidates == ["资产规模", "资本充足率"]


def test_requirement_parser_rejects_conflicting_model_output() -> None:
    parser = RequirementParser(generator=ConflictingGenerator())

    result = parser.parse(_build_request())

    assert result.spec is None
    assert result.failure_reason == "需求解析失败：模型改写了用户给定的因变量。"
    assert "需求解析失败：模型改写了用户给定的因变量。" in result.warnings

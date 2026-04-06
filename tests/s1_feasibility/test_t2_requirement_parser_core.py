"""S1-T2 需求解析核心契约测试。"""

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.spec.contracts import RequirementParseResult
from stata_agent.services.spec.requirement_parser import RequirementParser


class _FakeSpecGenerator:
    def parse_request(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(
            spec=ResearchSpec(
                topic=request.topic,
                dependent_variable=request.dependent_variable,
                independent_variables=request.independent_variables,
                entity_scope=request.entity_scope or "A股上市公司",
                time_start_year=2010,
                time_end_year=2023,
                control_variable_candidates=["资产规模"],
                analysis_grain_candidates=["firm-year"],
                analysis_frequency_hint="annual",
            )
        )


def test_requirement_parser_preserves_analysis_frequency_hint() -> None:
    """验证 parser 会把研究级频率写入最终的 ResearchSpec。"""
    parser = RequirementParser(generator=_FakeSpecGenerator())
    request = ResearchRequest(
        topic="企业数字化转型与盈利能力",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市公司",
        time_range="2010-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )

    result = parser.parse(request)

    assert result.failure_reason is None
    assert result.spec is not None
    assert result.spec.analysis_frequency_hint == "annual"

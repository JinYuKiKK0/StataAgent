from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.variable_requirements_builder import (
    VariableRequirementsBuilder,
)


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="银行季度数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_start_year=2010,
        time_end_year=2023,
        control_variable_candidates=["资本充足率", "资本充足率", "ROA", "拨备覆盖率"],
        analysis_grain_candidates=["bank-quarter"],
    )


def test_builder_outputs_variable_definitions_and_requirements() -> None:
    builder = VariableRequirementsBuilder()

    result = builder.build(_build_spec())

    assert result.variable_definitions
    assert result.data_requirements_draft.entity_scope == "A股上市银行"
    assert result.data_requirements_draft.time_start_year == 2010
    assert result.data_requirements_draft.time_end_year == 2023
    assert len(result.data_requirements_draft.items) == len(result.variable_definitions)


def test_builder_marks_core_variables_as_ready_and_locked() -> None:
    builder = VariableRequirementsBuilder()

    result = builder.build(_build_spec())

    dependent = next(
        item for item in result.variable_definitions if item.role == "dependent"
    )
    independent = next(
        item for item in result.variable_definitions if item.role == "independent"
    )

    assert dependent.variable_name == "ROA"
    assert dependent.is_locked is True
    assert dependent.slot_status == "ready"
    assert independent.variable_name == "数字化转型指数"
    assert independent.is_locked is True
    assert independent.slot_status == "ready"


def test_builder_deduplicates_and_reserves_control_slots() -> None:
    builder = VariableRequirementsBuilder()

    result = builder.build(_build_spec())
    controls = [item for item in result.variable_definitions if item.role == "control"]

    assert [item.variable_name for item in controls] == ["资本充足率", "拨备覆盖率"]
    assert all(item.slot_status == "pending_agent_completion" for item in controls)
    assert all(item.is_locked is False for item in controls)


def test_builder_applies_frequency_heuristic_and_unknown_fallback() -> None:
    builder = VariableRequirementsBuilder()
    result = builder.build(_build_spec())

    assert all(
        item.frequency_hint == "quarterly" for item in result.variable_definitions
    )

    annual_free_spec = _build_spec().model_copy(
        update={
            "topic": "银行数字化转型与风险承担",
            "control_variable_candidates": ["资产规模"],
        }
    )
    annual_free_result = builder.build(annual_free_spec)
    fallback_control = next(
        item
        for item in annual_free_result.variable_definitions
        if item.variable_name == "资产规模"
    )
    assert fallback_control.frequency_hint == "unknown"

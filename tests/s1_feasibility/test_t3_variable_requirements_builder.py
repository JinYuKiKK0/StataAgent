"""S1-T3 变量定义与数据需求清单测试。

该文件覆盖 `VariableRequirementsBuilder`，它位于需求解析之后、变量映射之前。
这个节点的职责是把 `ResearchSpec` 展开为变量定义表和数据需求表，明确
Y/X/控制变量的角色、锁定状态和频率提示，作为后续 CSMAR 探针映射的输入。
"""

from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.variable_requirements_builder import (
    VariableRequirementsBuilder,
)


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_start_year=2010,
        time_end_year=2023,
        control_variable_candidates=["资本充足率", "资本充足率", "ROA", "拨备覆盖率"],
        analysis_grain_candidates=["bank-quarter"],
        analysis_frequency_hint="quarterly",
    )


def test_builder_outputs_variable_definitions_and_requirements() -> None:
    """验证该节点会同步产出变量定义表和数据需求表这两份下游必需工件。"""
    builder = VariableRequirementsBuilder()

    result = builder.build(_build_spec())

    assert result.variable_definitions
    assert result.data_requirements_draft.entity_scope == "A股上市银行"
    assert result.data_requirements_draft.time_start_year == 2010
    assert result.data_requirements_draft.time_end_year == 2023
    assert len(result.data_requirements_draft.items) == len(result.variable_definitions)


def test_builder_marks_core_variables_as_ready_and_locked() -> None:
    """验证核心 Y/X 在工作流中被视为用户硬约束，因此必须直接锁定并标记为 ready。"""
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
    assert dependent.source_domain_hint == "pending_resolution"
    assert independent.variable_name == "数字化转型指数"
    assert independent.is_locked is True
    assert independent.slot_status == "ready"
    assert independent.source_domain_hint == "pending_resolution"


def test_builder_deduplicates_and_reserves_control_slots() -> None:
    """验证控制变量会去重并保留为待 agent 补全的弹性槽位，而不是被提前锁死。"""
    builder = VariableRequirementsBuilder()

    result = builder.build(_build_spec())
    controls = [item for item in result.variable_definitions if item.role == "control"]

    assert [item.variable_name for item in controls] == ["资本充足率", "拨备覆盖率"]
    assert all(item.slot_status == "pending_agent_completion" for item in controls)
    assert all(item.is_locked is False for item in controls)


def test_builder_copies_frequency_from_research_spec() -> None:
    """验证频率提示来自 parser 产出的研究级契约，而不是 builder 自己猜测。"""
    builder = VariableRequirementsBuilder()
    result = builder.build(_build_spec())

    assert all(
        item.frequency_hint == "quarterly" for item in result.variable_definitions
    )

    monthly_spec = _build_spec().model_copy(
        update={
            "analysis_frequency_hint": "monthly",
            "analysis_grain_candidates": ["bank-month"],
        }
    )
    monthly_result = builder.build(monthly_spec)

    assert all(item.frequency_hint == "monthly" for item in monthly_result.variable_definitions)

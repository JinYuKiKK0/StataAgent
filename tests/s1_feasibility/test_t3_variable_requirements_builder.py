"""S1-T3 变量定义与数据需求清单测试。

该文件覆盖 `VariableRequirementsBuilder`，它位于需求解析之后、变量映射之前。
这个节点的职责是把 `ResearchSpec` 展开为变量定义表和数据需求表，明确
Y/X/控制变量的角色、锁定状态和频率提示，作为后续 CSMAR 探针映射的输入。
"""

from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.services.spec.variable_requirements import (
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


def test_builder_deduplicates_and_reserves_control_slots() -> None:
    """验证控制变量会去重并保留为待 agent 补全的弹性槽位，而不是被提前锁死。"""
    builder = VariableRequirementsBuilder()

    result = builder.build(_build_spec())
    controls = [item for item in result.variable_definitions if item.role == "control"]

    assert [item.variable_name for item in controls] == ["资本充足率", "拨备覆盖率"]
    assert all(item.slot_status == "pending_agent_completion" for item in controls)
    assert all(item.is_locked is False for item in controls)

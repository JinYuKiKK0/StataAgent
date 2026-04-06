"""S1-T6 最低可行数据契约构建测试。

该文件覆盖 `DataContractBuilder`。它承接变量草案、探针覆盖摘要和字段绑定，
把它们整合为 Gateway 审批前的最小可行数据契约包。这个节点在工作流中
承担"把探针发现转成明确执行边界"的角色，决定哪些变量是不可退让的
Hard Contract，哪些变量可作为 Soft Contract 在后续装配阶段被白名单剔除。
"""

from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.services.contract.data_contract_builder import DataContractBuilder
from stata_agent.services.probe.contracts import ProbeCoverageResult


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_range="2010-2023",
        empirical_requirements="基准回归与描述统计",
    )


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_start_year=2010,
        time_end_year=2023,
        control_variable_candidates=["资本充足率", "资产规模"],
        analysis_grain_candidates=["bank-year"],
    )


def _build_variable_definitions() -> list[VariableDefinition]:
    return [
        VariableDefinition(
            variable_name="ROA",
            role="dependent",
            is_locked=True,
            slot_status="ready",
            frequency_hint="annual",
        ),
        VariableDefinition(
            variable_name="数字化转型指数",
            role="independent",
            is_locked=True,
            slot_status="ready",
            frequency_hint="annual",
        ),
        VariableDefinition(
            variable_name="资本充足率",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
        ),
    ]


def _build_bindings() -> list[VariableBinding]:
    return [
        VariableBinding(
            variable_name="ROA",
            table_code="FS_Comins",
            field_name="ROA",
            confidence=0.9,
            database_name="财务报表",
            contract_tier="hard",
            is_hard_contract=True,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
            table_name="利润表",
        ),
        VariableBinding(
            variable_name="数字化转型指数",
            table_code="BANK_DIGITAL_INDEX",
            field_name="DIGITAL_INDEX",
            confidence=0.9,
            database_name="银行专题",
            contract_tier="hard",
            is_hard_contract=True,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
            table_name="银行数字化转型指数",
        ),
        VariableBinding(
            variable_name="资本充足率",
            table_code="FS_Combas",
            field_name="CAPITAL_ADEQUACY",
            confidence=0.8,
            database_name="财务报表",
            contract_tier="soft",
            is_hard_contract=False,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
            substituted_from="风险加权资本比率",
            table_name="资产负债表",
        ),
    ]


def test_builder_generates_contract_bundle() -> None:
    """验证 S1-T6 会生成带粒度、时窗和软硬约束分层信息的完整契约包。"""
    builder = DataContractBuilder()

    result = builder.build(
        request=_build_request(),
        spec=_build_spec(),
        variable_definitions=_build_variable_definitions(),
        variable_bindings=_build_bindings(),
        probe_coverage=ProbeCoverageResult(
            hard_coverage_rate=1.0,
            soft_coverage_rate=0.5,
            hard_gaps=[],
            soft_gaps=["资本充足率"],
            key_alignment_ready=True,
            target_grain_ready=True,
        ),
    )

    assert result.analysis_grain == "bank-year"
    assert result.entity_scope == "A股上市银行"
    assert result.time_start_year == 2010
    assert result.time_end_year == 2023
    assert result.hard_contract_variables == ["ROA", "数字化转型指数"]
    assert result.allowed_soft_removals == ["资本充足率"]

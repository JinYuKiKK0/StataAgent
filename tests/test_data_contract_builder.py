import pytest

from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.services.data_contract_builder import DataContractBuilder


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
            source_domain_hint="bank_financials",
        ),
        VariableDefinition(
            variable_name="数字化转型指数",
            role="independent",
            is_locked=True,
            slot_status="ready",
            frequency_hint="annual",
            source_domain_hint="bank_topic",
        ),
        VariableDefinition(
            variable_name="资本充足率",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
            source_domain_hint="bank_financials",
        ),
    ]


def _build_bindings() -> list[VariableBinding]:
    return [
        VariableBinding(
            variable_name="ROA",
            table_name="FS_Comins",
            field_name="ROA",
            confidence=0.9,
            csmar_database="财务报表",
            contract_tier="hard",
            is_hard_contract=True,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
        ),
        VariableBinding(
            variable_name="数字化转型指数",
            table_name="BANK_DIGITAL_INDEX",
            field_name="DIGITAL_INDEX",
            confidence=0.9,
            csmar_database="银行专题",
            contract_tier="hard",
            is_hard_contract=True,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
        ),
        VariableBinding(
            variable_name="资本充足率",
            table_name="FS_Combas",
            field_name="CAPITAL_ADEQUACY",
            confidence=0.8,
            csmar_database="财务报表",
            contract_tier="soft",
            is_hard_contract=False,
            frequency_match=True,
            source="csmar_metadata_probe",
            evidence="alias命中=是",
            substituted_from="风险加权资本比率",
        ),
    ]


def test_builder_generates_contract_bundle() -> None:
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
    assert result.substitution_log == ["风险加权资本比率 -> 资本充足率 (FS_Combas.CAPITAL_ADEQUACY)"]


def test_builder_keeps_core_variables_outside_soft_removals() -> None:
    builder = DataContractBuilder()

    result = builder.build(
        request=_build_request(),
        spec=_build_spec(),
        variable_definitions=_build_variable_definitions(),
        variable_bindings=_build_bindings(),
        probe_coverage=ProbeCoverageResult(
            hard_coverage_rate=1.0,
            soft_coverage_rate=0.0,
            hard_gaps=[],
            soft_gaps=["ROA", "数字化转型指数", "资本充足率"],
            key_alignment_ready=True,
            target_grain_ready=True,
        ),
    )

    assert "ROA" not in result.allowed_soft_removals
    assert "数字化转型指数" not in result.allowed_soft_removals
    assert result.allowed_soft_removals == ["资本充足率"]


def test_builder_raises_when_protected_variable_leaks_to_soft_list() -> None:
    builder = DataContractBuilder()
    spec = _build_spec()
    definitions = _build_variable_definitions() + [
        VariableDefinition(
            variable_name="ROA",
            role="control",
            is_locked=False,
            slot_status="pending_agent_completion",
            frequency_hint="annual",
            source_domain_hint="bank_financials",
            note="人为构造的错误样本",
        )
    ]

    with pytest.raises(ValueError, match="核心变量不能进入允许自动剔除列表"):
        builder.build(
            request=_build_request(),
            spec=spec,
            variable_definitions=definitions,
            variable_bindings=_build_bindings(),
            probe_coverage=ProbeCoverageResult(
                hard_coverage_rate=1.0,
                soft_coverage_rate=0.0,
                hard_gaps=[],
                soft_gaps=["ROA"],
                key_alignment_ready=True,
                target_grain_ready=True,
            ),
        )

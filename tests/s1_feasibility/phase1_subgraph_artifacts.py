from __future__ import annotations

from stata_agent.domains.fetch.types import (
    DataContractBundle,
    ProbeCoverageResult,
    VariableProbeResult,
)
from stata_agent.domains.mapping.types import (
    VariableBinding,
    VariableMappingPlanItem,
    VariableMappingPlanResult,
    VariableMappingResult,
)
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import (
    DataRequirementItem,
    DataRequirementsDraft,
    RequirementParseResult,
    ResearchSpec,
    VariableDefinition,
    VariableRequirementsResult,
)


def build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行资本充足率与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_range="2018-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="银行资本充足率与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_start_year=2018,
        time_end_year=2023,
        control_variable_candidates=["资产规模"],
        analysis_grain_candidates=["bank-year"],
        analysis_frequency_hint="annual",
    )


def build_parse_result() -> RequirementParseResult:
    return RequirementParseResult(spec=build_spec(), warnings=[])


def build_builder_result() -> VariableRequirementsResult:
    definitions = [
        VariableDefinition(
            variable_name="ROA",
            role="dependent",
            is_locked=True,
            slot_status="ready",
            frequency_hint="annual",
            source_domain_hint="财务报表",
        ),
        VariableDefinition(
            variable_name="资本充足率",
            role="independent",
            is_locked=True,
            slot_status="ready",
            frequency_hint="annual",
            source_domain_hint="银行指标",
        ),
    ]
    return VariableRequirementsResult(
        variable_definitions=definitions,
        data_requirements_draft=DataRequirementsDraft(
            entity_scope="A股上市银行",
            time_start_year=2018,
            time_end_year=2023,
            items=[
                DataRequirementItem(
                    variable_name=item.variable_name,
                    role=item.role,
                    frequency_hint=item.frequency_hint,
                    source_domain_hint=item.source_domain_hint,
                    slot_status=item.slot_status,
                )
                for item in definitions
            ],
        ),
        warnings=[],
    )


def build_plan_result() -> VariableMappingPlanResult:
    return VariableMappingPlanResult(
        items=[
            VariableMappingPlanItem(
                variable_name="ROA",
                matched=True,
                database_name="财务报表",
                table_code="FS_Comins",
                table_name="利润表",
                field_name="ROA",
                field_label="资产回报率",
                frequency_match=True,
                evidence="已确认利润表字段。",
                trace_id="trace_map_roa",
            ),
            VariableMappingPlanItem(
                variable_name="资本充足率",
                matched=True,
                database_name="银行指标",
                table_code="BANK_Index",
                table_name="银行指标表",
                field_name="CAR",
                field_label="资本充足率",
                frequency_match=True,
                evidence="已确认银行指标字段。",
                trace_id="trace_map_car",
            ),
        ],
        warnings=["映射计划已生成。"],
    )


def build_mapping_result() -> VariableMappingResult:
    return VariableMappingResult(
        bindings=[
            VariableBinding(
                variable_name="ROA",
                table_code="FS_Comins",
                field_name="ROA",
                confidence=0.9,
                database_name="财务报表",
                contract_tier="hard",
                is_hard_contract=True,
                frequency_match=True,
                source="unit-test",
                evidence="已确认利润表字段。",
                trace_id="trace_map_roa",
                table_name="利润表",
            ),
            VariableBinding(
                variable_name="资本充足率",
                table_code="BANK_Index",
                field_name="CAR",
                confidence=0.9,
                database_name="银行指标",
                contract_tier="hard",
                is_hard_contract=True,
                frequency_match=True,
                source="unit-test",
                evidence="已确认银行指标字段。",
                trace_id="trace_map_car",
                table_name="银行指标表",
            ),
        ],
        hard_contract_variables=["ROA", "资本充足率"],
        warnings=["绑定物化已完成。"],
        resolved_variable_definitions=build_builder_result().variable_definitions,
    )


def build_probe_results() -> list[VariableProbeResult]:
    return [
        VariableProbeResult(
            variable_name="ROA",
            contract_tier="hard",
            table_code="FS_Comins",
            field_name="ROA",
            field_exists=True,
            frequency_match=True,
            query_count=100,
            is_accessible=True,
            trace_id="trace_probe_roa",
            query_fingerprint="fp_roa",
            validation_id="validation_roa",
            scope_level="time_scoped",
        ),
        VariableProbeResult(
            variable_name="资本充足率",
            contract_tier="hard",
            table_code="BANK_Index",
            field_name="CAR",
            field_exists=True,
            frequency_match=True,
            query_count=100,
            is_accessible=True,
            trace_id="trace_probe_car",
            query_fingerprint="fp_car",
            validation_id="validation_car",
            scope_level="time_scoped",
        ),
    ]


def build_coverage_result() -> ProbeCoverageResult:
    return ProbeCoverageResult(
        probe_results=build_probe_results(),
        hard_coverage_rate=1.0,
        soft_coverage_rate=1.0,
        key_alignment_ready=True,
        target_grain_ready=True,
        warnings=["覆盖摘要已生成。"],
    )


def build_contract() -> DataContractBundle:
    return DataContractBundle(
        hard_contract_variables=["ROA", "资本充足率"],
        soft_contract_variables=[],
        allowed_soft_removals=[],
        analysis_grain="bank-year",
        entity_scope="A股上市银行",
        entity_scope_inferred=False,
        time_start_year=2018,
        time_end_year=2023,
        empirical_requirements="构建基准双向固定效应模型",
        variable_definitions=build_builder_result().variable_definitions,
        variable_bindings=build_mapping_result().bindings,
        probe_coverage=build_coverage_result(),
        residual_risks=[],
        spec=build_spec(),
    )

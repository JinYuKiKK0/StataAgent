# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false

"""工作流根图对子图更新的可观测性测试。"""

from stata_agent.domains.fetch.types import DataContractBundle
from stata_agent.domains.fetch.types import ProbeCoverageResult
from stata_agent.domains.fetch.types import VariableProbeResult
from stata_agent.domains.mapping.types import VariableBinding
from stata_agent.domains.mapping.types import VariableMappingPlanItem
from stata_agent.domains.mapping.types import VariableMappingPlanResult
from stata_agent.domains.mapping.types import VariableMappingResult
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import DataRequirementsDraft
from stata_agent.domains.spec.types import DataRequirementItem
from stata_agent.domains.spec.types import RequirementParseResult
from stata_agent.domains.spec.types import ResearchSpec
from stata_agent.domains.spec.types import VariableDefinition
from stata_agent.domains.spec.types import VariableRequirementsResult
from stata_agent.workflow.orchestrator import ApplicationOrchestrator
from stata_agent.workflow.state import ResearchState


class _FakeParser:
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        return RequirementParseResult(spec=_build_spec(), warnings=[])


class _FakeBuilder:
    def build(self, spec: ResearchSpec) -> VariableRequirementsResult:
        definitions = _build_definitions()
        return VariableRequirementsResult(
            variable_definitions=definitions,
            data_requirements_draft=DataRequirementsDraft(
                entity_scope=spec.entity_scope,
                time_start_year=spec.time_start_year,
                time_end_year=spec.time_end_year,
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


class _FakeMapper:
    def plan_probe_mapping(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingPlanResult:
        return VariableMappingPlanResult(
            items=[
                VariableMappingPlanItem(
                    variable_name="ROA",
                    matched=True,
                    database_name="财务报表",
                    table_code="FS_Comins",
                    field_name="ROA",
                    frequency_match=True,
                    trace_id="trace_roa",
                ),
                VariableMappingPlanItem(
                    variable_name="资本充足率",
                    matched=True,
                    database_name="银行指标",
                    table_code="BANK_Index",
                    field_name="CAR",
                    frequency_match=True,
                    trace_id="trace_car",
                ),
            ]
        )

    def materialize_variable_bindings(
        self,
        *,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        planning_result: VariableMappingPlanResult,
    ) -> VariableMappingResult:
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
                    evidence="trace_roa",
                    trace_id="trace_roa",
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
                    evidence="trace_car",
                    trace_id="trace_car",
                ),
            ],
            hard_contract_variables=["ROA", "资本充足率"],
            resolved_variable_definitions=variable_definitions,
        )

    def map_probe_bindings(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
    ) -> VariableMappingResult:
        plan = self.plan_probe_mapping(
            request=request,
            spec=spec,
            variable_definitions=variable_definitions,
        )
        return self.materialize_variable_bindings(
            request=request,
            spec=spec,
            variable_definitions=variable_definitions,
            planning_result=plan,
        )

    def drain_tool_traces(self) -> list[object]:
        return []


class _FakeProbeExecutor:
    def run_field_probes(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> list[VariableProbeResult]:
        return [
            VariableProbeResult(
                variable_name="ROA",
                contract_tier="hard",
                table_code="FS_Comins",
                field_name="ROA",
                field_exists=True,
                frequency_match=True,
                query_count=12,
                is_accessible=True,
                scope_level="time_scoped",
            ),
            VariableProbeResult(
                variable_name="资本充足率",
                contract_tier="hard",
                table_code="BANK_Index",
                field_name="CAR",
                field_exists=True,
                frequency_match=True,
                query_count=12,
                is_accessible=True,
                scope_level="time_scoped",
            ),
        ]

    def summarize_coverage(
        self,
        spec: ResearchSpec,
        probe_results: list[VariableProbeResult],
    ) -> ProbeCoverageResult:
        return ProbeCoverageResult(
            probe_results=probe_results,
            hard_coverage_rate=1.0,
            soft_coverage_rate=1.0,
            key_alignment_ready=True,
            target_grain_ready=True,
        )

    def execute_coverage(
        self,
        spec: ResearchSpec,
        variable_bindings: list[VariableBinding],
    ) -> ProbeCoverageResult:
        raw_results = self.run_field_probes(spec, variable_bindings)
        return self.summarize_coverage(spec, raw_results)

    def drain_tool_traces(self) -> list[object]:
        return []


class _FakeContractBuilder:
    def build(
        self,
        request: ResearchRequest,
        spec: ResearchSpec,
        variable_definitions: list[VariableDefinition],
        variable_bindings: list[VariableBinding],
        probe_coverage: ProbeCoverageResult,
    ) -> DataContractBundle:
        return DataContractBundle(
            hard_contract_variables=["ROA", "资本充足率"],
            soft_contract_variables=[],
            allowed_soft_removals=[],
            analysis_grain="bank-year",
            entity_scope=spec.entity_scope,
            entity_scope_inferred=False,
            time_start_year=spec.time_start_year,
            time_end_year=spec.time_end_year,
            empirical_requirements=request.empirical_requirements,
            variable_definitions=variable_definitions,
            variable_bindings=variable_bindings,
            probe_coverage=probe_coverage,
            residual_risks=[],
            spec=spec,
        )


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行资本充足率与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_range="2018-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


def _build_spec() -> ResearchSpec:
    return ResearchSpec(
        topic="银行资本充足率与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_start_year=2018,
        time_end_year=2023,
        control_variable_candidates=[],
        analysis_grain_candidates=["bank-year"],
        analysis_frequency_hint="annual",
    )


def _build_definitions() -> list[VariableDefinition]:
    return [
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


def test_workflow_stream_exposes_nested_phase1_subgraph_updates() -> None:
    """验证根图流式执行时可观察到 S1 子图的内部节点更新。"""
    orchestrator = ApplicationOrchestrator(
        parser=_FakeParser(),
        builder=_FakeBuilder(),
        mapper=_FakeMapper(),
        probe_executor=_FakeProbeExecutor(),
        data_contract_builder=_FakeContractBuilder(),
    )

    chunks = orchestrator.compiled_graph.stream(
        ResearchState(request=_build_request()),
        config={"configurable": {"thread_id": "subgraph-test"}},
        stream_mode="updates",
        subgraphs=True,
        version="v2",
    )

    nested_nodes: list[str] = []
    for chunk in chunks:
        if chunk.get("type") != "updates":
            continue
        ns = chunk.get("ns", ())
        data = chunk.get("data", {})
        if not ns or not isinstance(data, dict) or not data:
            continue
        nested_nodes.append(next(iter(data)))

    assert nested_nodes[:7] == [
        "parse_request",
        "build_variable_requirements",
        "plan_probe_mapping",
        "materialize_variable_bindings",
        "run_field_probes",
        "summarize_probe_coverage",
        "build_data_contract",
    ]

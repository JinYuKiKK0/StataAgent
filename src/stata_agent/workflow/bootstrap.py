from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.providers.csmar import NodeScopedCsmarProviderFactory
from stata_agent.providers.llm import TongyiResearchSpecGenerator
from stata_agent.providers.llm import TongyiVariableMappingPlanner
from stata_agent.providers.settings import Settings
from stata_agent.providers.settings import get_settings
from stata_agent.services.contract.data_contract_builder import DataContractBuilder
from stata_agent.services.contract.ports import DataContractBuilderPort
from stata_agent.services.mapping.materialize_bindings import (
    VariableBindingMaterializer,
)
from stata_agent.services.mapping.plan_mapping import ProbeMappingPlanner
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.mapping.ports import ProbeMappingPlannerPort
from stata_agent.services.mapping.ports import VariableBindingMaterializerPort
from stata_agent.services.probe.executor import ProbeExecutor
from stata_agent.services.probe.ports import ProbeCoverageSummarizerPort
from stata_agent.services.probe.ports import ProbeExecutorPort
from stata_agent.services.probe.summarizer import ProbeCoverageSummarizer
from stata_agent.services.spec.ports import RequirementParserPort
from stata_agent.services.spec.ports import VariableRequirementsBuilderPort
from stata_agent.services.spec.requirement_parser import RequirementParser
from stata_agent.services.spec.variable_requirements import VariableRequirementsBuilder
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator
from stata_agent.workflow.stages.phase1_feasibility import Phase1OrchestratorPort


@dataclass(slots=True)
class ApplicationDependencies:
    settings: Settings
    phase1_orchestrator: Phase1OrchestratorPort
    csmar_provider: CsmarMetadataProviderPort


def build_application_dependencies(
    *,
    parser: RequirementParserPort | None = None,
    builder: VariableRequirementsBuilderPort | None = None,
    mapping_planner: ProbeMappingPlannerPort | None = None,
    binding_materializer: VariableBindingMaterializerPort | None = None,
    probe_executor: ProbeExecutorPort | None = None,
    probe_summarizer: ProbeCoverageSummarizerPort | None = None,
    data_contract_builder: DataContractBuilderPort | None = None,
    csmar_provider: CsmarMetadataProviderPort | None = None,
    phase1_orchestrator: Phase1OrchestratorPort | None = None,
    settings_factory: Callable[[], Settings] = get_settings,
) -> ApplicationDependencies:
    settings = settings_factory()
    resolved_csmar_provider = csmar_provider or CsmarBridgeClient.from_settings(settings)
    resolved_phase1 = phase1_orchestrator or Phase1FeasibilityOrchestrator(
        parser=parser or RequirementParser(TongyiResearchSpecGenerator(settings)),
        builder=builder or VariableRequirementsBuilder(),
        mapping_planner=mapping_planner
        or ProbeMappingPlanner(
            metadata_provider=resolved_csmar_provider,
            planner=TongyiVariableMappingPlanner(settings),
            scope_factory=NodeScopedCsmarProviderFactory(),
        ),
        binding_materializer=binding_materializer or VariableBindingMaterializer(),
        probe_executor=probe_executor or ProbeExecutor(metadata_provider=resolved_csmar_provider),
        probe_summarizer=probe_summarizer or ProbeCoverageSummarizer(),
        data_contract_builder=data_contract_builder or DataContractBuilder(),
    )
    return ApplicationDependencies(
        settings=settings,
        phase1_orchestrator=resolved_phase1,
        csmar_provider=resolved_csmar_provider,
    )

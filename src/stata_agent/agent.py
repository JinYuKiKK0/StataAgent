"""LangGraph Agent 入口，供 LangSmith Agent Server 使用。

这里不再维护独立编排逻辑，只复用 ApplicationOrchestrator 的共享图构建。
LangSmith/LangGraph Server 负责持久化，因此默认导出的 graph 不附带 checkpointer。
"""

from stata_agent.services.contract.ports import DataContractBuilderPort
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.mapping.ports import ProbeMappingPlannerPort
from stata_agent.services.mapping.ports import VariableBindingMaterializerPort
from stata_agent.services.probe.ports import ProbeCoverageSummarizerPort
from stata_agent.services.probe.ports import ProbeExecutorPort
from stata_agent.services.spec.ports import RequirementParserPort
from stata_agent.services.spec.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.orchestrator import ApplicationOrchestrator
from stata_agent.workflow.stages.phase1_feasibility import Phase1OrchestratorPort


def build_agent_graph(
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
):
    orchestrator = ApplicationOrchestrator(
        parser=parser,
        builder=builder,
        mapping_planner=mapping_planner,
        binding_materializer=binding_materializer,
        probe_executor=probe_executor,
        probe_summarizer=probe_summarizer,
        data_contract_builder=data_contract_builder,
        csmar_provider=csmar_provider,
        phase1_orchestrator=phase1_orchestrator,
        checkpointer_factory=None,
    )
    return orchestrator.compiled_graph


graph = build_agent_graph()

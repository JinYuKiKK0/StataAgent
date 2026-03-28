"""LangGraph Agent 入口，供 LangSmith Agent Server 使用。

这里不再维护独立编排逻辑，只复用 ApplicationOrchestrator 的共享图构建。
LangSmith/LangGraph Server 负责持久化，因此默认导出的 graph 不附带 checkpointer。
"""

from stata_agent.workflow.orchestrator import ApplicationOrchestrator
from stata_agent.workflow.ports import CsmarMetadataProviderPort
from stata_agent.workflow.ports import DataContractBuilderPort
from stata_agent.workflow.ports import Phase1OrchestratorPort
from stata_agent.workflow.ports import ProbeExecutorPort
from stata_agent.workflow.ports import RequirementParserPort
from stata_agent.workflow.ports import VariableMapperPort
from stata_agent.workflow.ports import VariableRequirementsBuilderPort


def build_agent_graph(
    *,
    parser: RequirementParserPort | None = None,
    builder: VariableRequirementsBuilderPort | None = None,
    mapper: VariableMapperPort | None = None,
    probe_executor: ProbeExecutorPort | None = None,
    data_contract_builder: DataContractBuilderPort | None = None,
    csmar_provider: CsmarMetadataProviderPort | None = None,
    phase1_orchestrator: Phase1OrchestratorPort | None = None,
):
    orchestrator = ApplicationOrchestrator(
        parser=parser,
        builder=builder,
        mapper=mapper,
        probe_executor=probe_executor,
        data_contract_builder=data_contract_builder,
        csmar_provider=csmar_provider,
        phase1_orchestrator=phase1_orchestrator,
        checkpointer_factory=None,
    )
    return orchestrator.compiled_graph


graph = build_agent_graph()

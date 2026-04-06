from __future__ import annotations

import os
from collections.abc import Generator

import pytest

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.audit import InMemoryAuditStore
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.providers.csmar.node_scoped_client import NodeScopedCsmarProviderFactory
from stata_agent.providers.llm import TongyiResearchSpecGenerator
from stata_agent.providers.llm import TongyiVariableMappingPlanner
from stata_agent.providers.settings import Settings, get_settings
from stata_agent.services.contract.data_contract_builder import DataContractBuilder
from stata_agent.services.mapping.materialize_bindings import VariableBindingMaterializer
from stata_agent.services.mapping.plan_mapping import ProbeMappingPlanner
from stata_agent.services.probe.executor import ProbeExecutor
from stata_agent.services.probe.summarizer import ProbeCoverageSummarizer
from stata_agent.services.spec.requirement_parser import RequirementParser
from stata_agent.services.spec.variable_requirements import VariableRequirementsBuilder
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator

_RUN_LIVE_TESTS_ENV = "RUN_LIVE_API_TESTS"


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _require_live_tests_enabled() -> None:
    if not _is_truthy(os.getenv(_RUN_LIVE_TESTS_ENV)):
        pytest.skip(
            f"需要设置 {_RUN_LIVE_TESTS_ENV}=1 才会执行真实 Tongyi/CSMAR 集成测试。"
        )


@pytest.fixture(scope="session")
def live_settings() -> Settings:
    _require_live_tests_enabled()
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="session")
def live_csmar_ready(live_settings: Settings) -> None:
    if not live_settings.csmar_account or live_settings.csmar_password is None:
        pytest.skip("缺少 CSMAR_ACCOUNT 或 CSMAR_PASSWORD，无法执行真实 CSMAR 测试。")
    default_mcp_workdir = (live_settings.workspace_dir.parent / "CSMAR-Data-MCP").resolve()
    configured_mcp_workdir = (
        live_settings.csmar_mcp_workdir.resolve()
        if live_settings.csmar_mcp_workdir is not None
        else default_mcp_workdir
    )
    if not configured_mcp_workdir.exists():
        pytest.skip(
            f"未找到 CSMAR MCP 工作目录：{configured_mcp_workdir}，无法执行真实 CSMAR 测试。"
        )


@pytest.fixture(scope="session")
def live_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行资本充足率与盈利能力",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_range="2018-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


@pytest.fixture(scope="session")
def failing_live_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行资本充足率与盈利能力",
        dependent_variable="不存在的核心变量",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_range="2018-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )


@pytest.fixture(scope="session")
def live_parser(live_settings: Settings) -> RequirementParser:
    generator = TongyiResearchSpecGenerator(live_settings)
    return RequirementParser(generator=generator)


@pytest.fixture(scope="session")
def live_csmar_provider(
    live_settings: Settings,
    live_csmar_ready: None,
) -> CsmarBridgeClient:
    return CsmarBridgeClient.from_settings(live_settings)


@pytest.fixture(scope="session")
def live_phase1_orchestrator(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_settings: Settings,
) -> Phase1FeasibilityOrchestrator:
    return Phase1FeasibilityOrchestrator(
        parser=live_parser,
        builder=VariableRequirementsBuilder(),
        mapping_planner=ProbeMappingPlanner(
            metadata_provider=live_csmar_provider,
            planner=TongyiVariableMappingPlanner(live_settings),
            scope_factory=NodeScopedCsmarProviderFactory(),
        ),
        binding_materializer=VariableBindingMaterializer(),
        probe_executor=ProbeExecutor(metadata_provider=live_csmar_provider),
        probe_summarizer=ProbeCoverageSummarizer(),
        data_contract_builder=DataContractBuilder(),
        audit_store=InMemoryAuditStore(),
    )


@pytest.fixture(scope="session", autouse=True)
def clear_settings_cache_after_session() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

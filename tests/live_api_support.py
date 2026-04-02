from __future__ import annotations

import importlib.util
import os
from collections.abc import Generator

import pytest

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.csmar import CsmarBridgeClient
from stata_agent.providers.llm import TongyiResearchSpecGenerator
from stata_agent.providers.llm import TongyiVariableSemanticJudge
from stata_agent.providers.settings import Settings, get_settings
from stata_agent.services.data_contract_builder import DataContractBuilder
from stata_agent.services.probe_executor import ProbeExecutor
from stata_agent.services.requirement_parser import RequirementParser
from stata_agent.services.variable_mapper import VariableMapper
from stata_agent.services.variable_requirements_builder import VariableRequirementsBuilder
from stata_agent.workflow.stages.phase1_feasibility import Phase1FeasibilityOrchestrator

_RUN_LIVE_TESTS_ENV = "RUN_LIVE_API_TESTS"


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _require_live_tests_enabled() -> None:
    if not _is_truthy(os.getenv(_RUN_LIVE_TESTS_ENV)):
        pytest.skip(
            f"需要设置 {_RUN_LIVE_TESTS_ENV}=1 才会执行真实 Tongyi/CSMAR 集成测试。"
        )


def _require_csmar_sdk_installed() -> None:
    if importlib.util.find_spec("csmarapi") is None:
        pytest.skip("未检测到 csmarapi SDK，无法执行真实 CSMAR 集成测试。")


@pytest.fixture(scope="session")
def live_settings() -> Settings:
    _require_live_tests_enabled()
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="session")
def live_csmar_ready(live_settings: Settings) -> None:
    _require_csmar_sdk_installed()
    if not live_settings.csmar_account or live_settings.csmar_password is None:
        pytest.skip("缺少 CSMAR_ACCOUNT 或 CSMAR_PASSWORD，无法执行真实 CSMAR 测试。")


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
    password = live_settings.csmar_password
    if password is None:
        pytest.skip("缺少 CSMAR_PASSWORD，无法执行真实 CSMAR 测试。")
    return CsmarBridgeClient(
        account=live_settings.csmar_account,
        password=password.get_secret_value(),
        language=live_settings.csmar_language,
    )


@pytest.fixture(scope="session")
def live_phase1_orchestrator(
    live_parser: RequirementParser,
    live_csmar_provider: CsmarBridgeClient,
    live_settings: Settings,
) -> Phase1FeasibilityOrchestrator:
    return Phase1FeasibilityOrchestrator(
        parser=live_parser,
        builder=VariableRequirementsBuilder(),
        mapper=VariableMapper(
            metadata_provider=live_csmar_provider,
            semantic_judge=TongyiVariableSemanticJudge(live_settings),
        ),
        probe_executor=ProbeExecutor(metadata_provider=live_csmar_provider),
        data_contract_builder=DataContractBuilder(),
    )


@pytest.fixture(scope="session", autouse=True)
def clear_settings_cache_after_session() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

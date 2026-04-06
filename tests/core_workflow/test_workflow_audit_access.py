"""工作流审计读取入口测试。"""

from pathlib import Path
from typing import cast

from pydantic import SecretStr

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.settings import Settings
from stata_agent.services.contract.ports import DataContractBuilderPort
from stata_agent.services.mapping.ports import CsmarMetadataProviderPort
from stata_agent.services.mapping.ports import ProbeMappingPlannerPort
from stata_agent.services.mapping.ports import VariableBindingMaterializerPort
from stata_agent.services.probe.ports import ProbeCoverageSummarizerPort
from stata_agent.services.probe.ports import ProbeExecutorPort
from stata_agent.services.spec.contracts import RequirementParseResult
from stata_agent.services.spec.ports import VariableRequirementsBuilderPort
from stata_agent.workflow.orchestrator import ApplicationOrchestrator
from stata_agent.workflow.types import RunStage


class _FailingParser:
    def parse(self, request: ResearchRequest) -> RequirementParseResult:
        del request
        return RequirementParseResult(
            raw_response_text='{"malformed": true}',
            parsing_error="schema mismatch",
            failure_reason="需求解析失败：Tongyi 未产出可用的研究规范。",
            warnings=["schema mismatch"],
        )


class _UnusedBuilder:
    def build(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("parse 失败后不应进入变量需求构建。")


class _UnusedMappingPlanner:
    def plan_probe_mapping(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("parse 失败后不应进入映射规划。")

    def drain_tool_traces(self) -> list[object]:
        return []


class _UnusedBindingMaterializer:
    def materialize_variable_bindings(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("parse 失败后不应进入 binding 物化。")


class _UnusedProbeExecutor:
    def run_field_probes(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("parse 失败后不应进入 probe。")

    def drain_tool_traces(self) -> list[object]:
        return []


class _UnusedProbeSummarizer:
    def summarize_coverage(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("parse 失败后不应进入覆盖摘要。")


class _UnusedContractBuilder:
    def build(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("parse 失败后不应进入契约构建。")


class _UnusedMetadataProvider:
    def list_databases(self) -> list[str]:
        raise AssertionError("该测试不应触发 CSMAR provider。")

    def list_tables(self, database_name: str) -> list[object]:
        del database_name
        raise AssertionError("该测试不应触发 CSMAR provider。")

    def get_table_schema(self, table_code: str) -> object:
        del table_code
        raise AssertionError("该测试不应触发 CSMAR provider。")

    def probe_field_availability(self, request: object) -> object:
        del request
        raise AssertionError("该测试不应触发 CSMAR provider。")


def _build_request() -> ResearchRequest:
    return ResearchRequest(
        topic="银行资本充足率与ROA",
        dependent_variable="ROA",
        independent_variables=["资本充足率"],
        entity_scope="A股上市银行",
        time_range="2018-2023",
        empirical_requirements="构建基准回归模型",
    )


def _build_settings() -> Settings:
    return Settings(
        workspace_dir=Path("/tmp/stata_agent_tests"),
        dashscope_api_key=SecretStr("test-key"),
        tongyi_model="qwen-test",
    )


def test_orchestrator_exposes_parse_audit_by_audit_ref() -> None:
    """验证工作流状态只暴露审计引用，详细原始响应需经专用读取入口获取。"""
    orchestrator = ApplicationOrchestrator(
        parser=_FailingParser(),
        builder=cast(VariableRequirementsBuilderPort, _UnusedBuilder()),
        mapping_planner=cast(ProbeMappingPlannerPort, _UnusedMappingPlanner()),
        binding_materializer=cast(
            VariableBindingMaterializerPort,
            _UnusedBindingMaterializer(),
        ),
        probe_executor=cast(ProbeExecutorPort, _UnusedProbeExecutor()),
        probe_summarizer=cast(
            ProbeCoverageSummarizerPort,
            _UnusedProbeSummarizer(),
        ),
        data_contract_builder=cast(DataContractBuilderPort, _UnusedContractBuilder()),
        csmar_provider=cast(CsmarMetadataProviderPort, _UnusedMetadataProvider()),
        settings_factory=_build_settings,
    )

    state, thread_id = orchestrator.run(_build_request())

    assert state.stage is RunStage.FAILED
    parse_audit = state.workflow_audit.node_audits["parse_request"]
    assert parse_audit.audit_refs

    audit_record = orchestrator.read_audit_record(thread_id, parse_audit.audit_refs[0])

    assert audit_record is not None
    assert audit_record.kind == "parse_request"
    assert audit_record.payload["raw_response_text"] == '{"malformed": true}'
    assert audit_record.payload["parsing_error"] == "schema mismatch"

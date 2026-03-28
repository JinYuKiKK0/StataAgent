"""包级启动与 CLI 入口测试。

该文件主要覆盖 S1-T1 的入口能力：包暴露核心契约、CLI 能展示帮助、
`research` 命令能把用户输入送入应用编排器。它位于整个工作流的最外层，
负责把研究请求送进状态机，因此这里的测试更关注启动契约、参数校验和
用户可见输出，而不是某个内部业务节点的算法细节。
"""

from typer.testing import CliRunner

import pytest


def test_package_exposes_core_contracts() -> None:
    """验证安装后的顶层包能暴露最小可用契约，保证入口模块可被外部导入。"""
    from stata_agent import __version__
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.workflow.state import ResearchState

    request = ResearchRequest(
        topic="银行数字化转型与风险承担",
        dependent_variable="ROA",
        independent_variables=["数字化转型指数"],
        entity_scope="A股上市银行",
        time_range="2010-2023",
        empirical_requirements="构建基准双向固定效应模型",
    )
    state = ResearchState(request=request)

    assert __version__ == "0.1.0"
    assert state.request == request


def test_cli_help_is_available() -> None:
    """验证 CLI 启动面正常，用户在进入工作流前能看到帮助和命令说明。"""
    from stata_agent.interfaces.cli import app

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "StataAgent" in result.stdout


def test_research_command_with_valid_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 `research` 命令能把合法输入送入工作流入口，并输出 Phase 1 产物摘要。

    这是 S1-T1 的核心功能性测试：CLI 处在工作流最前端，负责收集研究题目、
    Y/X、样本范围与时间范围，然后把这些信息交给 `ApplicationOrchestrator`。
    当下游返回 `SPECIFIED` 状态时，CLI 还承担“把解析结果转译给用户”的角色，
    因此这里会检查 `ResearchSpec`、变量定义表和数据需求表是否进入输出。
    """
    from stata_agent.domains.spec.types import DataRequirementItem
    from stata_agent.domains.spec.types import DataRequirementsDraft
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.domains.spec.types import RequirementParseResult, ResearchSpec
    from stata_agent.domains.spec.types import VariableDefinition
    from stata_agent.interfaces.cli import app
    from stata_agent.workflow.types import RunStage

    class SuccessfulOrchestrator:
        def run(self, request: ResearchRequest):
            from stata_agent.workflow.state import ResearchState

            state = ResearchState(
                request=request,
                stage=RunStage.SPECIFIED,
                spec=ResearchSpec(
                    topic=request.topic,
                    dependent_variable=request.dependent_variable,
                    independent_variables=request.independent_variables,
                    entity_scope=request.entity_scope,
                    time_start_year=2010,
                    time_end_year=2023,
                    control_variable_candidates=["资产规模", "资本充足率"],
                    analysis_grain_candidates=["bank-year"],
                ),
                parse_result=RequirementParseResult(
                    raw_response_text="structured output",
                    warnings=["数字化口径需后续映射确认"],
                ),
                variable_definitions=[
                    VariableDefinition(
                        variable_name="ROA",
                        role="dependent",
                        is_locked=True,
                        slot_status="ready",
                        frequency_hint="annual",
                        source_domain_hint="bank_financials",
                    ),
                    VariableDefinition(
                        variable_name="资产规模",
                        role="control",
                        is_locked=False,
                        slot_status="pending_agent_completion",
                        frequency_hint="annual",
                        source_domain_hint="bank_financials",
                    ),
                ],
                data_requirements_draft=DataRequirementsDraft(
                    entity_scope=request.entity_scope,
                    time_start_year=2010,
                    time_end_year=2023,
                    items=[
                        DataRequirementItem(
                            variable_name="ROA",
                            role="dependent",
                            frequency_hint="annual",
                            source_domain_hint="bank_financials",
                            slot_status="ready",
                        ),
                        DataRequirementItem(
                            variable_name="资产规模",
                            role="control",
                            frequency_hint="annual",
                            source_domain_hint="bank_financials",
                            slot_status="pending_agent_completion",
                        ),
                    ],
                ),
            )
            return state, "test-thread-1"

    monkeypatch.setattr(
        "stata_agent.interfaces.cli.ApplicationOrchestrator", SuccessfulOrchestrator
    )
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic",
            "银行数字化转型与风险承担",
            "--y",
            "ROA",
            "--x",
            "数字化转型指数",
            "--entity",
            "A股上市银行",
            "--time",
            "2010-2023",
        ],
    )

    assert result.exit_code == 0
    assert "✓ 研究请求已完成需求解析" in result.stdout
    assert "银行数字化转型与风险承担" in result.stdout
    assert "ResearchSpec 摘要" in result.stdout
    assert "变量定义表" in result.stdout
    assert "数据需求表" in result.stdout
    assert "bank-year" in result.stdout
    assert "资产规模" in result.stdout


def test_research_command_with_parse_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 CLI 会把需求解析失败转译成明确的终端错误，而不是静默退出。"""
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.domains.spec.types import RequirementParseResult
    from stata_agent.interfaces.cli import app
    from stata_agent.workflow.types import RunStage

    class FailingOrchestrator:
        def run(self, request: ResearchRequest):
            from stata_agent.workflow.state import ResearchState

            state = ResearchState(
                request=request,
                stage=RunStage.FAILED,
                parse_result=RequirementParseResult(
                    raw_response_text="bad output",
                    failure_reason="需求解析失败：模型没有提供候选分析粒度。",
                ),
                notes=["需求解析失败：模型没有提供候选分析粒度。"],
            )
            return state, "test-thread-2"

    monkeypatch.setattr(
        "stata_agent.interfaces.cli.ApplicationOrchestrator", FailingOrchestrator
    )
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic",
            "银行数字化转型与风险承担",
            "--y",
            "ROA",
            "--x",
            "数字化转型指数",
            "--entity",
            "A股上市银行",
            "--time",
            "2010-2023",
        ],
    )

    assert result.exit_code == 1
    assert "需求解析阶段失败" in result.stdout
    assert "模型没有提供候选分析粒度" in result.stdout


def test_research_command_with_missing_tongyi_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证工作流尚未启动前就会拦截缺失的 Tongyi 配置，避免进入半初始化状态。"""
    from stata_agent.interfaces.cli import app
    from stata_agent.workflow.orchestrator import WorkflowBootstrapError

    class BootstrapFailingOrchestrator:
        def run(self, request):
            raise WorkflowBootstrapError(["DASHSCOPE_API_KEY: Field required"])

    monkeypatch.setattr(
        "stata_agent.interfaces.cli.ApplicationOrchestrator",
        BootstrapFailingOrchestrator,
    )

    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic",
            "银行数字化转型与风险承担",
            "--y",
            "ROA",
            "--x",
            "数字化转型指数",
            "--entity",
            "A股上市银行",
            "--time",
            "2010-2023",
        ],
    )

    assert result.exit_code == 1
    assert "DASHSCOPE_API_KEY" in result.stdout


def test_research_command_missing_required_fields() -> None:
    """验证 CLI 对研究请求必填字段做入口级校验，防止无效请求进入状态机。"""
    from stata_agent.interfaces.cli import app

    # 测试缺少 --topic
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--y",
            "ROA",
            "--x",
            "数字化转型指数",
            "--entity",
            "A股上市银行",
            "--time",
            "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--topic" in result.stderr or "Error" in result.stderr

    # 测试缺少 --y
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic",
            "银行数字化转型与风险承担",
            "--x",
            "数字化转型指数",
            "--entity",
            "A股上市银行",
            "--time",
            "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--y" in result.stderr or "Error" in result.stderr

    # 测试缺少 --x
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic",
            "银行数字化转型与风险承担",
            "--y",
            "ROA",
            "--entity",
            "A股上市银行",
            "--time",
            "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--x" in result.stderr or "Error" in result.stderr

    # 测试缺少 --entity
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic",
            "银行数字化转型与风险承担",
            "--y",
            "ROA",
            "--x",
            "数字化转型指数",
            "--time",
            "2010-2023",
        ],
    )

    assert result.exit_code != 0
    assert "--entity" in result.stderr or "Error" in result.stderr

    # 测试缺少 --time
    result = CliRunner().invoke(
        app,
        [
            "research",
            "--topic",
            "银行数字化转型与风险承担",
            "--y",
            "ROA",
            "--x",
            "数字化转型指数",
            "--entity",
            "A股上市银行",
        ],
    )

    assert result.exit_code != 0
    assert "--time" in result.stderr or "Error" in result.stderr

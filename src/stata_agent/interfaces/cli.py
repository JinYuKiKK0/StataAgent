import typer
from rich.console import Console
from rich.table import Table

from pydantic import ValidationError
from typing import NoReturn

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.workflow.orchestrator import ApplicationOrchestrator, WorkflowBootstrapError
from stata_agent.workflow.state import ResearchState
from stata_agent.workflow.types import RunStage

app = typer.Typer(
    name="StataAgent",
    help="StataAgent CLI for local empirical-analysis workflows.",
)
console = Console()


@app.callback(invoke_without_command=True)
def entrypoint(ctx: typer.Context) -> None:
    """StataAgent CLI for local empirical-analysis workflows."""
    if ctx.invoked_subcommand is None:
        about()


@app.command()
def about() -> None:
    orchestrator = ApplicationOrchestrator()
    console.print(f"{_load_app_name(orchestrator)} project skeleton is ready.")


@app.command()
def research(
    topic: str = typer.Option(..., "--topic", "-t", help="研究题目，如：银行数字化转型与风险承担"),
    dependent_variable: str = typer.Option(..., "--y", "-y", help="因变量 Y，如：ROA"),
    independent_variables: list[str] = typer.Option(..., "--x", "-x", help="自变量 X 列表，可多次指定"),
    entity_scope: str = typer.Option(..., "--entity", "-e", help="样本范围，如：A股上市公司"),
    time_range: str = typer.Option(..., "--time", "-r", help="时间范围，如：2010-2023"),
    empirical_requirements: str = typer.Option(
        "构建基准回归模型", "--requirements", "-R", help="实证要求"
    ),
) -> None:
    """提交单次实证分析请求。"""
    request = _build_request(
        topic=topic,
        dependent_variable=dependent_variable,
        independent_variables=independent_variables,
        entity_scope=entity_scope,
        time_range=time_range,
        empirical_requirements=empirical_requirements,
    )
    orchestrator = ApplicationOrchestrator()
    try:
        state: ResearchState = orchestrator.run(request)
    except WorkflowBootstrapError as exc:
        _raise_bootstrap_exit(exc)
    _render_research_summary(state)
    if state.stage is RunStage.FAILED:
        raise typer.Exit(code=1)

def main() -> None:
    app()


def _load_app_name(orchestrator: ApplicationOrchestrator) -> str:
    try:
        return orchestrator.app_name()
    except WorkflowBootstrapError as exc:
        _raise_bootstrap_exit(exc)


def _raise_bootstrap_exit(exc: WorkflowBootstrapError) -> NoReturn:
    console.print("\n[bold red]✗ 配置层启动阻截：配置环境校验失败[/bold red]")
    console.print("[yellow]确保项目根目录下存在 `.env` 文件，且其包含如下受约束配置：[/yellow]")
    for detail in exc.details:
        console.print(f"  - [cyan]{detail}[/cyan]")
    raise typer.Exit(code=1) from exc


def _build_request(
    *,
    topic: str,
    dependent_variable: str,
    independent_variables: list[str],
    entity_scope: str,
    time_range: str,
    empirical_requirements: str,
) -> ResearchRequest:
    try:
        return ResearchRequest(
            topic=topic,
            dependent_variable=dependent_variable,
            independent_variables=independent_variables,
            entity_scope=entity_scope,
            time_range=time_range,
            empirical_requirements=empirical_requirements,
        )
    except ValidationError as exc:
        console.print("\n[bold red]✗ 输入参数校验失败：[/bold red]")
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            console.print(f"  - [cyan]{field}[/cyan]: {err['msg']}")
        raise typer.Exit(code=1) from exc


def _render_research_summary(state: ResearchState) -> None:
    if state.stage is not RunStage.FAILED:
        console.print("\n[bold green]✓ 研究请求已完成需求解析[/bold green]\n")
    else:
        console.print("\n[bold red]✗ 研究请求在需求解析阶段失败[/bold red]\n")

    table = Table(title="研究请求摘要")
    table.add_column("字段", style="cyan")
    table.add_column("值", style="white")

    table.add_row("研究题目", state.request.topic)
    table.add_row("因变量 (Y)", state.request.dependent_variable)
    table.add_row("自变量 (X)", ", ".join(state.request.independent_variables))
    table.add_row("样本范围", state.request.entity_scope)
    table.add_row("时间范围", state.request.time_range)
    table.add_row("实证要求", state.request.empirical_requirements)
    table.add_row("当前阶段", state.stage.value)

    console.print(table)
    if state.spec is not None:
        _render_spec_summary(state)
    if state.variable_definitions is not None:
        _render_variable_definitions(state)
    if state.data_requirements_draft is not None:
        _render_data_requirements(state)
    if state.parse_result is not None:
        _render_parse_audit(state)
    if state.probe_coverage_result is not None:
        _render_probe_coverage(state)
    console.print(f"\n[dim]工作流状态 ID: {state.stage}[/dim]")


def _render_spec_summary(state: ResearchState) -> None:
    if state.spec is None:
        return

    table = Table(title="ResearchSpec 摘要")
    table.add_column("字段", style="cyan")
    table.add_column("值", style="white")

    table.add_row("解析主题", state.spec.topic)
    table.add_row("样本范围", state.spec.entity_scope)
    table.add_row("时间边界", f"{state.spec.time_start_year}-{state.spec.time_end_year}")
    table.add_row("候选分析粒度", ", ".join(state.spec.analysis_grain_candidates))
    table.add_row(
        "控制变量候选",
        ", ".join(state.spec.control_variable_candidates) if state.spec.control_variable_candidates else "无",
    )

    console.print(table)


def _render_parse_audit(state: ResearchState) -> None:
    if state.parse_result is None:
        return

    table = Table(title="需求解析审计")
    table.add_column("字段", style="cyan")
    table.add_column("值", style="white")

    if state.parse_result.failure_reason is not None:
        table.add_row("失败原因", state.parse_result.failure_reason)
    if state.parse_result.parsing_error is not None:
        table.add_row("结构化解析错误", state.parse_result.parsing_error)
    if state.parse_result.warnings:
        table.add_row("Warnings", " | ".join(state.parse_result.warnings))
    if state.parse_result.raw_response_text:
        table.add_row("原始响应", state.parse_result.raw_response_text)

    if table.row_count > 0:
        console.print(table)


def _render_variable_definitions(state: ResearchState) -> None:
    if state.variable_definitions is None:
        return

    table = Table(title="变量定义表")
    table.add_column("变量")
    table.add_column("角色")
    table.add_column("锁定")
    table.add_column("槽位状态")
    table.add_column("频率")
    table.add_column("候选数据域")

    for definition in state.variable_definitions:
        table.add_row(
            definition.variable_name,
            definition.role,
            "是" if definition.is_locked else "否",
            definition.slot_status,
            definition.frequency_hint,
            definition.source_domain_hint,
        )

    console.print(table)


def _render_data_requirements(state: ResearchState) -> None:
    if state.data_requirements_draft is None:
        return

    summary = Table(title="数据需求表")
    summary.add_column("字段", style="cyan")
    summary.add_column("值", style="white")
    summary.add_row("样本范围", state.data_requirements_draft.entity_scope)
    summary.add_row(
        "时间边界",
        f"{state.data_requirements_draft.time_start_year}-{state.data_requirements_draft.time_end_year}",
    )
    summary.add_row("需求条目数", str(len(state.data_requirements_draft.items)))
    console.print(summary)


def _render_probe_coverage(state: ResearchState) -> None:
    if state.probe_coverage_result is None:
        return

    summary = Table(title="探针覆盖摘要")
    summary.add_column("字段", style="cyan")
    summary.add_column("值", style="white")
    summary.add_row("Hard 覆盖率", f"{state.probe_coverage_result.hard_coverage_rate:.0%}")
    summary.add_row("Soft 覆盖率", f"{state.probe_coverage_result.soft_coverage_rate:.0%}")
    summary.add_row(
        "关键主键可对齐",
        "是" if state.probe_coverage_result.key_alignment_ready else "否",
    )
    summary.add_row(
        "目标粒度可得",
        "是" if state.probe_coverage_result.target_grain_ready else "否",
    )
    summary.add_row(
        "Hard 缺口",
        "、".join(state.probe_coverage_result.hard_gaps) if state.probe_coverage_result.hard_gaps else "无",
    )
    summary.add_row(
        "Soft 缺口",
        "、".join(state.probe_coverage_result.soft_gaps) if state.probe_coverage_result.soft_gaps else "无",
    )
    console.print(summary)

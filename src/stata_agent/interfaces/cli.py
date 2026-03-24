import typer
from rich.console import Console
from rich.table import Table

from pydantic import ValidationError

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.settings import SettingsError, get_settings
from stata_agent.workflow.orchestrator import ApplicationOrchestrator
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
    settings = _load_settings()
    console.print(f"{settings.app_name} project skeleton is ready.")


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
    _load_settings()
    request = _build_request(
        topic=topic,
        dependent_variable=dependent_variable,
        independent_variables=independent_variables,
        entity_scope=entity_scope,
        time_range=time_range,
        empirical_requirements=empirical_requirements,
    )
    orchestrator = ApplicationOrchestrator()
    state = orchestrator.run(request)
    _render_research_summary(state)
    if state.stage is RunStage.FAILED:
        raise typer.Exit(code=1)

def main() -> None:
    app()


def _load_settings():
    try:
        return get_settings()
    except SettingsError as exc:
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
    if state.stage is RunStage.SPECIFIED:
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
    if state.parse_result is not None:
        _render_parse_audit(state)
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

import typer
from rich.console import Console
from rich.table import Table

from pydantic import ValidationError

from stata_agent.domains.request.types import ResearchRequest
from stata_agent.providers.settings import SettingsError, get_settings
from stata_agent.workflow.orchestrator import ApplicationOrchestrator
from stata_agent.workflow.state import ResearchState

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
    request = _build_request(
        topic=topic,
        dependent_variable=dependent_variable,
        independent_variables=independent_variables,
        entity_scope=entity_scope,
        time_range=time_range,
        empirical_requirements=empirical_requirements,
    )
    orchestrator = ApplicationOrchestrator()
    state = orchestrator.create_initial_state(request)
    _render_research_summary(state)

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
    console.print("\n[bold green]✓ 请求已接收并验证通过[/bold green]\n")

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
    console.print(f"\n[dim]工作流状态 ID: {state.stage}[/dim]")

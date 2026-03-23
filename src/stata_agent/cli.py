import typer
from rich.console import Console

from stata_agent.config import get_settings

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
    settings = get_settings()
    console.print(f"{settings.app_name} project skeleton is ready.")


def main() -> None:
    app()

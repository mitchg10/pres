from __future__ import annotations

import subprocess
import sys

import typer
from rich.console import Console
from rich.table import Table

from presentation_maker import generator
from presentation_maker.wizard import run_wizard

app = typer.Typer(
    name="pres",
    help="Presentation wizard — scaffold Quarto RevealJS presentations.",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


@app.command()
def new() -> None:
    """Interactively scaffold a new Quarto RevealJS presentation."""
    try:
        config = run_wizard()
        target = generator.scaffold_presentation(config)
        console.print(f"\n[bold green]Created:[/bold green] {target}")
        console.print(f"[dim]To preview:[/dim] pres preview {config.slug}")
    except FileExistsError as exc:
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(code=0)


@app.command(name="list")
def list_presentations() -> None:
    """List all presentations in the presentations/ directory."""
    presentations = generator.list_presentations()
    if not presentations:
        console.print("[dim]No presentations found. Run 'pres new' to create one.[/dim]")
        return
    table = Table(title="Presentations", show_header=True, header_style="bold blue")
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Path", style="dim")
    for pres in presentations:
        table.add_row(pres["slug"], pres["title"], pres["path"])
    console.print(table)


@app.command()
def preview(name: str = typer.Argument(..., help="Presentation slug to preview")) -> None:
    """Preview a presentation with quarto (runs from project root so images resolve)."""
    pres_path = generator.get_presentations_dir() / name / "index.qmd"
    if not pres_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No presentation named '{name}'.")
        raise typer.Exit(code=1)
    subprocess.run(
        ["quarto", "preview", str(pres_path)],
        cwd=str(generator.PROJECT_ROOT),
        check=True,
    )


@app.command()
def open(name: str = typer.Argument(..., help="Presentation slug to open in Finder")) -> None:
    """Open a presentation directory in Finder (macOS only)."""
    if sys.platform != "darwin":
        err_console.print("[bold red]Error:[/bold red] 'pres open' is macOS only.")
        raise typer.Exit(code=1)
    pres_path = generator.get_presentations_dir() / name
    if not pres_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No presentation named '{name}'.")
        raise typer.Exit(code=1)
    subprocess.run(["open", str(pres_path)], check=True)

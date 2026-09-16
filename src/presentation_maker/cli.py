from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from presentation_maker import export as export_module
from presentation_maker import generator
from presentation_maker import network
from presentation_maker import pdf as pdf_module
from presentation_maker import poster_generator
from presentation_maker import screenshot as screenshot_module
from presentation_maker.capture_models import CaptureOptions, CaptureResult
from presentation_maker.poster_wizard import run_poster_wizard
from presentation_maker.wizard import run_wizard

def _watch_partials(partials_dir: Path, main_file: Path, stop: threading.Event) -> None:
    if not partials_dir.exists():
        return
    mtimes: dict[Path, float] = {
        f: f.stat().st_mtime for f in partials_dir.glob("**/*.qmd")
    }
    while not stop.is_set():
        time.sleep(0.5)
        for qmd in partials_dir.glob("**/*.qmd"):
            mtime = qmd.stat().st_mtime
            if mtimes.get(qmd) != mtime:
                mtimes[qmd] = mtime
                main_file.touch()
                break


def _print_network_banner(port: int) -> None:
    """Print the LAN URL (and a scannable QR code) for a --network preview."""
    ip = network.get_lan_ip()
    if ip is None:
        err_console.print(
            "[yellow]Warning:[/yellow] Could not detect a LAN IP address — "
            "are you connected to WiFi?\n"
            f"[dim]Serving on port {port} anyway.[/dim]\n"
        )
        return

    url = f"http://{ip}:{port}"
    console.print(f"\n[bold]On your phone (same WiFi):[/bold] [bold cyan]{url}[/bold cyan]\n")

    try:
        qr = network.render_qr(url)
    except RuntimeError as exc:
        err_console.print(f"[yellow]Warning:[/yellow] {exc}")
        qr = None
    if qr:
        print(qr)

    console.print(
        "\n[dim]Anyone on this WiFi network can view the presentation while the "
        "preview is running.\nmacOS may ask you to allow incoming connections — "
        "click Allow.[/dim]\n"
    )


def _run_capture(capture: Callable[[], CaptureResult]) -> CaptureResult:
    """Run a capture, turning its failure modes into readable CLI errors."""
    try:
        return capture()
    except ImportError:
        err_console.print(
            "[bold red]Error:[/bold red] playwright is not installed.\n"
            "Run: [cyan]uv add playwright && playwright install chromium[/cyan]"
        )
        raise typer.Exit(code=1)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError:
        err_console.print("[bold red]Error:[/bold red] 'quarto render' failed. Check your index.qmd.")
        raise typer.Exit(code=1)


def _print_capture(result: CaptureResult, *, as_json: bool) -> None:
    """Report a capture — as JSON for tooling, otherwise for a person to read."""
    if as_json:
        print(result.model_dump_json(indent=2))
        return

    console.print(
        f"\n[bold green]Captured {len(result.images)} image(s):[/bold green] {result.out_dir}"
    )
    for image in result.images:
        console.print(f"  [dim]{image.name}[/dim]")
    if result.contact_sheet:
        console.print(f"[bold]Contact sheet:[/bold] {result.contact_sheet}")
    if result.report:
        console.print(f"[bold]Report:[/bold] {result.report}")
    for warning in (*result.overflow, *result.failed_requests, *result.console_errors):
        err_console.print(f"[yellow]![/yellow] {warning}")


app = typer.Typer(
    name="pres",
    help="Presentation wizard — scaffold Quarto RevealJS presentations.",
    no_args_is_help=True,
)

poster_app = typer.Typer(
    name="poster",
    help="Poster wizard — scaffold Quarto HTML academic posters (24×36 in).",
    no_args_is_help=True,
)

app.add_typer(poster_app, name="poster")

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
def preview(
    name: str = typer.Argument(..., help="Presentation slug to preview"),
    network_access: bool = typer.Option(
        False,
        "--network",
        "-n",
        help="Also serve on the local network so a phone or tablet can view it.",
    ),
    port: int = typer.Option(
        network.DEFAULT_PORT,
        "--port",
        help="Port to bind when --network is used.",
    ),
) -> None:
    """Preview a presentation with quarto (runs from project root so images resolve)."""
    pres_path = generator.get_presentations_dir() / name / "index.qmd"
    if not pres_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No presentation named '{name}'.")
        raise typer.Exit(code=1)

    cmd = ["quarto", "preview", str(pres_path)]
    if network_access:
        try:
            bound_port = network.find_free_port(port)
        except RuntimeError as exc:
            err_console.print(f"[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(code=1)
        cmd = [*cmd, "--host", "0.0.0.0", "--port", str(bound_port)]
        _print_network_banner(bound_port)

    partials_dir = pres_path.parent / "partials"
    stop = threading.Event()
    threading.Thread(
        target=_watch_partials,
        args=(partials_dir, pres_path, stop),
        daemon=True,
    ).start()
    try:
        subprocess.run(cmd, cwd=str(generator.PROJECT_ROOT), check=True)
    except subprocess.CalledProcessError:
        err_console.print("[bold red]Error:[/bold red] 'quarto preview' failed.")
        raise typer.Exit(code=1)
    finally:
        stop.set()


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


@app.command()
def pdf(name: str = typer.Argument(..., help="Presentation slug to export as PDF")) -> None:
    """Export a presentation to PDF using headless Chromium."""
    pres_path = generator.get_presentations_dir() / name
    if not pres_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No presentation named '{name}'.")
        raise typer.Exit(code=1)
    try:
        output = pdf_module.export_presentation_pdf(name, pres_path, generator.PROJECT_ROOT)
        console.print(f"\n[bold green]PDF saved:[/bold green] {output}")
    except ImportError:
        err_console.print(
            "[bold red]Error:[/bold red] playwright is not installed.\n"
            "Run: [cyan]uv add playwright && playwright install chromium[/cyan]"
        )
        raise typer.Exit(code=1)
    except FileNotFoundError as exc:
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError:
        err_console.print("[bold red]Error:[/bold red] 'quarto render' failed. Check your index.qmd.")
        raise typer.Exit(code=1)


@app.command(name="export")
def export_html(
    name: str = typer.Argument(..., help="Presentation slug to export"),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Write here instead of <slug>-standalone.html in the deck directory.",
    ),
) -> None:
    """Export a presentation as one self-contained HTML file (resources embedded)."""
    pres_path = generator.get_presentations_dir() / name
    if not pres_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No presentation named '{name}'.")
        raise typer.Exit(code=1)
    try:
        written = export_module.export_standalone_html(name, pres_path, output=output)
    except (FileNotFoundError, FileExistsError, RuntimeError) as exc:
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    size_mb = written.stat().st_size / 1_000_000
    console.print(f"\n[bold green]Standalone HTML saved:[/bold green] {written}")
    console.print(f"[dim]{size_mb:.1f} MB — one file, no index_files/ needed.[/dim]")
    console.print(
        "[dim]Chalkboard and the speaker-notes window are unavailable in an "
        "embedded deck.[/dim]"
    )


@app.command()
def shot(
    name: str = typer.Argument(..., help="Presentation slug to screenshot"),
    slides: str = typer.Option(
        "all",
        "--slide",
        "-s",
        help="all | index (3) | slide id | range (2-5) | comma-separated mix.",
    ),
    fragments: bool = typer.Option(
        False, "--fragments", "-f", help="Capture each fragment reveal step."
    ),
    frames: int = typer.Option(
        0, "--frames", help="Capture N timed frames per slide (for animations)."
    ),
    interval: int = typer.Option(
        400, "--interval", help="Milliseconds between timed frames."
    ),
    contact_sheet: bool = typer.Option(
        False, "--contact-sheet", help="Also write one tiled grid image of every capture."
    ),
    out: Path = typer.Option(
        None, "--out", "-o", help="Output directory [default: build/shots/<slug>]."
    ),
    width: int = typer.Option(1280, "--width", help="Viewport width in pixels."),
    height: int = typer.Option(720, "--height", help="Viewport height in pixels."),
    scale: float = typer.Option(1.0, "--scale", help="Device scale factor."),
    wait: int = typer.Option(1200, "--wait", help="Extra settle delay in milliseconds."),
    render: bool = typer.Option(
        True, "--render/--no-render", help="Re-render when the build is out of date."
    ),
    url: str = typer.Option(
        None, "--url", help="Capture a running 'pres preview' URL instead of the built file."
    ),
    report: bool = typer.Option(
        True, "--report/--no-report", help="Write capture-report.md alongside the images."
    ),
    as_json: bool = typer.Option(False, "--json", help="Print the result as JSON."),
) -> None:
    """Screenshot slides to PNG so you can see how a change actually renders."""
    pres_path = generator.get_presentations_dir() / name
    if not pres_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No presentation named '{name}'.")
        raise typer.Exit(code=1)
    if fragments and frames:
        err_console.print(
            "[bold red]Error:[/bold red] --fragments and --frames capture different "
            "things; use one at a time."
        )
        raise typer.Exit(code=1)

    options = CaptureOptions(
        slides=slides,
        fragments=fragments,
        frames=frames,
        interval_ms=interval,
        contact_sheet=contact_sheet,
        out_dir=out,
        width=width,
        height=height,
        scale=scale,
        wait_ms=wait,
        render=render,
        url=url,
        report=report,
        quiet=as_json,
    )
    result = _run_capture(
        lambda: screenshot_module.capture_presentation(
            name, pres_path, generator.PROJECT_ROOT, options
        )
    )
    _print_capture(result, as_json=as_json)


# ── Poster subcommands ────────────────────────────────────────────────────────

@poster_app.command(name="new")
def poster_new() -> None:
    """Interactively scaffold a new 24×36 in academic poster."""
    try:
        config = run_poster_wizard()
        target = poster_generator.scaffold_poster(config)
        console.print(f"\n[bold green]Created:[/bold green] {target}")
        console.print(f"[dim]To preview:[/dim] pres poster preview {config.slug}")
    except FileExistsError as exc:
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(code=0)


@poster_app.command(name="list")
def poster_list() -> None:
    """List all posters in the posters/ directory."""
    posters = poster_generator.list_posters()
    if not posters:
        console.print("[dim]No posters found. Run 'pres poster new' to create one.[/dim]")
        return
    table = Table(title="Posters", show_header=True, header_style="bold blue")
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Path", style="dim")
    for poster in posters:
        table.add_row(poster["slug"], poster["title"], poster["path"])
    console.print(table)


@poster_app.command(name="preview")
def poster_preview(name: str = typer.Argument(..., help="Poster slug to preview")) -> None:
    """Preview a poster with quarto (runs from project root so paths resolve)."""
    poster_path = generator.get_posters_dir() / name / "index.qmd"
    if not poster_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No poster named '{name}'.")
        raise typer.Exit(code=1)
    try:
        subprocess.run(
            ["quarto", "preview", str(poster_path)],
            cwd=str(generator.PROJECT_ROOT),
            check=True,
        )
    except subprocess.CalledProcessError:
        err_console.print("[bold red]Error:[/bold red] 'quarto preview' failed.")
        raise typer.Exit(code=1)


@poster_app.command(name="shot")
def poster_shot(
    name: str = typer.Argument(..., help="Poster slug to screenshot"),
    out: Path = typer.Option(
        None, "--out", "-o", help="Output directory [default: build/shots/<slug>]."
    ),
    width: int = typer.Option(
        1152, "--width", help="Viewport width in pixels (half of 24in at 96dpi)."
    ),
    height: int = typer.Option(
        1728, "--height", help="Viewport height in pixels (half of 36in at 96dpi)."
    ),
    scale: float = typer.Option(1.0, "--scale", help="Device scale factor."),
    wait: int = typer.Option(1200, "--wait", help="Extra settle delay in milliseconds."),
    render: bool = typer.Option(
        True, "--render/--no-render", help="Re-render when the build is out of date."
    ),
    report: bool = typer.Option(
        True, "--report/--no-report", help="Write capture-report.md alongside the image."
    ),
    as_json: bool = typer.Option(False, "--json", help="Print the result as JSON."),
) -> None:
    """Screenshot a poster to PNG so you can see how a change actually renders."""
    poster_path = generator.get_posters_dir() / name
    if not poster_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No poster named '{name}'.")
        raise typer.Exit(code=1)

    options = CaptureOptions(
        out_dir=out,
        width=width,
        height=height,
        scale=scale,
        wait_ms=wait,
        render=render,
        report=report,
        quiet=as_json,
    )
    result = _run_capture(
        lambda: screenshot_module.capture_poster(
            name, poster_path, generator.PROJECT_ROOT, options
        )
    )
    _print_capture(result, as_json=as_json)


@poster_app.command(name="pdf")
def poster_pdf(name: str = typer.Argument(..., help="Poster slug to export as PDF")) -> None:
    """Export a poster to a 24×36 in PDF using headless Chromium."""
    poster_path = generator.get_posters_dir() / name
    if not poster_path.exists():
        err_console.print(f"[bold red]Error:[/bold red] No poster named '{name}'.")
        raise typer.Exit(code=1)
    try:
        output = pdf_module.export_poster_pdf(name, poster_path, generator.PROJECT_ROOT)
        console.print(f"\n[bold green]PDF saved:[/bold green] {output}")
    except ImportError:
        err_console.print(
            "[bold red]Error:[/bold red] playwright is not installed.\n"
            "Run: [cyan]uv add playwright && playwright install chromium[/cyan]"
        )
        raise typer.Exit(code=1)
    except FileNotFoundError as exc:
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError:
        err_console.print("[bold red]Error:[/bold red] 'quarto render' failed. Check your index.qmd.")
        raise typer.Exit(code=1)

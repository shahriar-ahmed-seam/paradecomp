"""Authoritative Typer and Rich telemetry CLI for ParaDecomp."""

from __future__ import annotations

import asyncio
from typing import List

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from paradecomp import __version__
from paradecomp.analyzer.independence import SubtaskIndependenceAnalyzer
from paradecomp.benchmarks.runner import BenchmarkRunner
from paradecomp.core.models import SubtaskContract
from paradecomp.workloads.deep_research import DeepResearchEngine, ResearchFacet

app = typer.Typer(
    name="paradecomp",
    help="High-Breadth Parallel Subtask Decomposition & Elastic Scatter-Gather Engine.",
    no_args_is_help=True,
)
console = Console()


@app.command("version")
def version_cmd() -> None:
    """Print package version."""
    console.print(f"[bold cyan]ParaDecomp[/bold cyan] v{__version__}")


@app.command("analyze")
def analyze_cmd(
    subtasks: List[str] = typer.Option(
        [
            "Optics: High-NA numerical aperture",
            "Transistors: GAA nanosheet 2nm yields",
            "Packaging: Direct Cu-Cu hybrid bonding",
            "Power: Backside power delivery routing",
        ],
        "--subtask",
        "-s",
        help="Subtask definitions to evaluate.",
    ),
    threshold: float = typer.Option(
        0.70,
        "--threshold",
        "-t",
        help="Minimum orthogonality threshold for fan-out gating.",
    ),
) -> None:
    """Evaluate mathematical subtask independence and gating decision."""
    analyzer = SubtaskIndependenceAnalyzer(threshold=threshold)
    contracts: List[SubtaskContract] = [
        SubtaskContract(
            subtask_id=f"st_{i}",
            parent_task_id="task_cli",
            title=st.split(":")[0].strip() if ":" in st else f"Task {i}",
            query_or_instruction=st.split(":")[1].strip() if ":" in st else st,
        )
        for i, st in enumerate(subtasks)
    ]

    matrix = analyzer.analyze_matrix(contracts)

    table = Table(
        title="Pairwise Subtask Orthogonality Matrix",
        header_style="bold magenta",
        border_style="bright_black",
    )
    table.add_column("Subtask ID", style="cyan")
    table.add_column("Title", style="white")
    for sid in matrix.subtask_ids:
        table.add_column(sid, justify="center")

    for i, sid in enumerate(matrix.subtask_ids):
        row = [sid, contracts[i].title]
        for sid_other in matrix.subtask_ids:
            if sid == sid_other:
                row.append("[dim]1.00[/dim]")
            else:
                ov = matrix.pairwise_overlap.get(sid, {}).get(sid_other, 0.0)
                cp = matrix.pairwise_coupling.get(sid, {}).get(sid_other, 0.0)
                ortho = 1.0 - (0.5 * ov + 0.5 * cp)
                style = "green" if ortho >= threshold else "yellow"
                row.append(f"[{style}]{ortho:.2f}[/{style}]")
        table.add_row(*row)

    console.print(table)

    verdict_style = (
        "bold green" if matrix.gating_verdict.value == "PARALLEL_FAN_OUT" else "bold red"
    )
    panel_text = (
        f"[bold]Mean Orthogonality:[/bold] {matrix.mean_orthogonality:.4f} "
        f"(Threshold: {threshold:.2f})\n"
        f"[bold]Gating Verdict:[/bold] "
        f"[{verdict_style}]{matrix.gating_verdict.value}[/{verdict_style}]\n"
        f"[bold]Justification:[/bold] {matrix.justification}"
    )
    console.print(
        Panel(
            panel_text,
            title="[bold]Independence Gating Decision[/bold]",
            border_style="bright_black",
        )
    )


@app.command("research")
def research_cmd(
    topic: str = typer.Option(
        "Sub-2nm Semiconductor Lithography Scaling",
        "--topic",
        "-q",
        help="Master research topic.",
    ),
    num_facets: int = typer.Option(
        10,
        "--facets",
        "-f",
        help="Number of orthogonal sub-facets to explore concurrently.",
    ),
    sources_per_facet: int = typer.Option(
        30,
        "--sources",
        "-n",
        help="Sources to gather per facet.",
    ),
) -> None:
    """Execute high-breadth Deep Research across N concurrent sub-agents."""
    engine = DeepResearchEngine()
    facets = [
        ResearchFacet(
            facet_id=f"f_{i:02d}",
            title=f"{topic} Vector {i:02d}",
            query=f"Exploration branch {i:02d} for {topic}",
            expected_sources=sources_per_facet,
        )
        for i in range(num_facets)
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(f"Dispatched {num_facets} concurrent workers...", total=None)
        output = asyncio.run(engine.run(topic, facets))

    table = Table(
        title=f"Deep Research Telemetry: {topic}",
        border_style="bright_black",
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold green")

    table.add_row("Execution Strategy", output.strategy_used.value)
    table.add_row("Concurrent Subtasks", str(output.total_subtasks))
    table.add_row("Successful Workers", str(output.successful_subtasks))
    table.add_row("Total Sources Gathered", str(output.total_sources_gathered))
    table.add_row("Wall-Clock Duration", f"{output.wall_clock_duration_ms:.2f} ms")
    table.add_row("Coverage Throughput", f"{output.coverage_per_second:.1f} sources/sec")

    if output.verification:
        v = output.verification
        table.add_row("Critic Verdict", v.verdict.value)
        table.add_row("Critic Confidence", f"{v.confidence_score:.4f}")
        table.add_row("Rechecked Sources", str(v.rechecked_sources_count))
        table.add_row("Deduplicated Count", str(v.deduplicated_count))

    console.print(table)


@app.command("benchmark")
def benchmark_cmd(
    num_subtasks: int = typer.Option(
        10,
        "--subtasks",
        "-n",
        help="Number of concurrent subtasks.",
    ),
    sources_per_subtask: int = typer.Option(
        30,
        "--sources",
        "-s",
        help="Target sources per subtask.",
    ),
) -> None:
    """Run comparative benchmark: Serial Agent Bottleneck vs ParaDecomp Swarm."""
    runner = BenchmarkRunner()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Executing serial vs parallel benchmark...", total=None)
        report = asyncio.run(
            runner.run(
                num_facets=num_subtasks,
                sources_per_facet=sources_per_subtask,
                simulated_io_ms=15.0,
            )
        )

    table = Table(
        title="Multi-Agent Decomposition Benchmark: Serial vs ParaDecomp",
        border_style="bright_black",
        header_style="bold magenta",
    )
    table.add_column("Architecture", style="bold")
    table.add_column("Sources Pulled", justify="right")
    table.add_column("Wall-Clock (ms)", justify="right")
    table.add_column("Throughput (src/s)", justify="right")
    table.add_column("Breadth Gain", justify="right")
    table.add_column("Critic Verdict", justify="center")

    table.add_row(
        "[red]Serial Agent (Sequential)[/red]",
        f"{report.serial_sources_pulled}",
        f"{report.serial_duration_ms:.1f}",
        f"{report.serial_sources_per_second:.1f}",
        "1.0x (Baseline)",
        "[dim]N/A (Bottleneck)[/dim]",
    )
    table.add_row(
        f"[green]ParaDecomp ({num_subtasks} Sub-agents)[/green]",
        f"[bold green]{report.parallel_sources_pulled}[/bold green]",
        f"{report.parallel_duration_ms:.1f}",
        f"{report.parallel_sources_per_second:.1f}",
        f"[bold green]{report.breadth_multiplier:.1f}x[/bold green]",
        f"[green]{report.critic_verdict.value}[/green]",
    )

    console.print(table)


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host interface to bind."),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on."),
    reload: bool = typer.Option(False, "--reload", help="Enable live auto-reload."),
) -> None:
    """Launch Developer Telemetry REST Server & Web UI."""
    console.print(
        f"[bold cyan]Launching ParaDecomp Telemetry Workbench on http://{host}:{port}[/bold cyan]"
    )
    uvicorn.run("paradecomp.ui.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()

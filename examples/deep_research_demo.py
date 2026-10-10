"""End-to-end demonstration of high-breadth Deep Research with ParaDecomp."""

import asyncio

from rich.console import Console
from rich.table import Table

from paradecomp.workloads.deep_research import DeepResearchEngine, ResearchFacet

console = Console()


async def main() -> None:
    engine = DeepResearchEngine()

    facets = [
        ResearchFacet(
            facet_id="optics",
            title="High-NA EUV Optics",
            query="0.55 numerical aperture anamorphic mirror specifications",
            expected_sources=30,
        ),
        ResearchFacet(
            facet_id="nanosheets",
            title="GAA Nanosheet Yields",
            query="Inner spacer etch selectivity in 2nm logic nodes",
            expected_sources=30,
        ),
        ResearchFacet(
            facet_id="backside_power",
            title="Backside Power Delivery",
            query="Buried power rail contact resistance and IR drop",
            expected_sources=30,
        ),
        ResearchFacet(
            facet_id="hybrid_bonding",
            title="Direct Cu-Cu Hybrid Bonding",
            query="Wafer-to-wafer sub-micron pitch alignment tolerances",
            expected_sources=30,
        ),
    ]

    console.print("[bold cyan]Dispatching ParaDecomp High-Breadth Research Swarm...[/bold cyan]")
    output = await engine.run(
        objective_title="Advanced Semiconductor Scaling Vectors",
        facets=facets,
    )

    table = Table(title="Deep Research Aggregation Summary", border_style="bright_black")
    table.add_column("Property", style="dim")
    table.add_column("Value", style="bold green")

    table.add_row("Execution Strategy", output.strategy_used.value)
    table.add_row("Total Subtasks", str(output.total_subtasks))
    table.add_row("Successful Workers", str(output.successful_subtasks))
    table.add_row("Total Sources Pulled", str(output.total_sources_gathered))
    table.add_row("Wall-Clock Time", f"{output.wall_clock_duration_ms:.2f} ms")
    table.add_row("Throughput", f"{output.coverage_per_second:.1f} src/s")

    if output.verification:
        table.add_row("Critic Verdict", output.verification.verdict.value)
        table.add_row("Critic Confidence", f"{output.verification.confidence_score:.4f}")

    console.print(table)


if __name__ == "__main__":
    asyncio.run(main())

"""Demonstration of using ParaDecomp as a high-breadth LangChain / LlamaIndex tool."""

import asyncio

from rich.console import Console

from paradecomp.adapters.providers import LangChainToolAdapter

console = Console()


async def main() -> None:
    tool = LangChainToolAdapter()

    console.print(f"[bold cyan]Tool Name:[/bold cyan] {tool.name}")
    console.print(f"[bold cyan]Description:[/bold cyan] {tool.description}\n")

    query = "Quantum Computing Cryogenic Control Circuits"
    console.print(f"[dim]Executing tool with query: '{query}'...[/dim]")

    result = await tool.arun(query=query, num_facets=4)

    console.print(f"[bold green]Execution Strategy:[/bold green] {result['strategy']}")
    console.print(f"[bold green]Sources Pulled:[/bold green] {result['total_sources']}")
    console.print(f"[bold green]Throughput:[/bold green] {result['coverage_per_second']:.1f} src/s")

    if result.get("verification"):
        v = result["verification"]
        console.print(f"[bold green]Critic Verdict:[/bold green] {v['verdict']}")
        console.print(f"[bold green]Critic Confidence:[/bold green] {v['confidence_score']}")


if __name__ == "__main__":
    asyncio.run(main())

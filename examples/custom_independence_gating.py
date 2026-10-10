"""Demonstration of subtask independence analysis and dynamic gating."""

from rich.console import Console
from rich.panel import Panel

from paradecomp.analyzer.independence import SubtaskIndependenceAnalyzer
from paradecomp.core.models import SubtaskContract

console = Console()


def evaluate_set(name: str, contracts: list[SubtaskContract]) -> None:
    analyzer = SubtaskIndependenceAnalyzer(threshold=0.70)
    matrix = analyzer.analyze_matrix(contracts)

    style = "green" if matrix.gating_verdict.value == "PARALLEL_FAN_OUT" else "red"
    console.print(
        Panel(
            f"[bold]Subtasks Count:[/bold] {len(contracts)}\n"
            f"[bold]Mean Orthogonality:[/bold] {matrix.mean_orthogonality:.4f}\n"
            f"[bold]Gating Decision:[/bold] [{style}]{matrix.gating_verdict.value}[/{style}]\n"
            f"[dim]{matrix.justification}[/dim]",
            title=f"[bold]{name}[/bold]",
            border_style="bright_black",
        )
    )


def main() -> None:
    # 1. Orthogonal Independent Subtasks
    independent = [
        SubtaskContract(
            subtask_id="st_1",
            parent_task_id="p1",
            title="Taiwan Foundry Analysis",
            query_or_instruction="Evaluate 3nm wafer capacity in Tainan.",
        ),
        SubtaskContract(
            subtask_id="st_2",
            parent_task_id="p1",
            title="Arizona Fab Buildout",
            query_or_instruction="Analyze cleanroom construction schedules.",
        ),
        SubtaskContract(
            subtask_id="st_3",
            parent_task_id="p1",
            title="Kumamoto Packaging Line",
            query_or_instruction="Review substrate supply chain availability.",
        ),
    ]
    evaluate_set("Orthogonal Set (Parallel Fan-Out Expected)", independent)

    # 2. Coupled Sequential Subtasks
    coupled = [
        SubtaskContract(
            subtask_id="step_1",
            parent_task_id="p2",
            title="Lexer Phase",
            query_or_instruction="Tokenize source code stream.",
        ),
        SubtaskContract(
            subtask_id="step_2",
            parent_task_id="p2",
            title="Parser Phase",
            query_or_instruction="Construct AST from tokens.",
            dependencies=["step_1"],
        ),
        SubtaskContract(
            subtask_id="step_3",
            parent_task_id="p2",
            title="Codegen Phase",
            query_or_instruction="Emit LLVM bytecode from AST.",
            dependencies=["step_2"],
        ),
    ]
    evaluate_set("Coupled Serial Chain (Monolithic Fallback Expected)", coupled)


if __name__ == "__main__":
    main()

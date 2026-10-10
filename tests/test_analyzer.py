"""Unit tests for SubtaskIndependenceAnalyzer and topological wave levelizer."""

import pytest

from paradecomp.analyzer.independence import (
    SubtaskIndependenceAnalyzer,
    topological_sort_waves,
)
from paradecomp.core.models import (
    ExecutionStrategy,
    SubtaskContract,
    TaskObjective,
)


def test_independent_subtasks_authorization():
    analyzer = SubtaskIndependenceAnalyzer(threshold=0.60)
    obj = TaskObjective(
        title="High-Breadth Market Analysis",
        description="Analyze 4 distinct geographic semiconductor supply chains concurrently.",
    )
    facets = [
        ("Taiwan TSMC Foundries", "Analyze 3nm node yields in Tainan Fab 18."),
        (
            "US Arizona Fab Buildout",
            "Assess labor and equipment installation timelines in Phoenix.",
        ),
        ("Japan Kumamoto Facility", "Track automotive legacy node ramp in JASM Kumamoto."),
        ("European Dresden Megafab", "Examine European Chips Act subsidies for Saxony."),
    ]
    plan = analyzer.decompose(obj, facets)

    assert plan.strategy == ExecutionStrategy.PARALLEL_FAN_OUT
    assert plan.is_parallel is True
    assert plan.total_subtasks == 4
    assert plan.independence_matrix is not None
    assert plan.independence_matrix.mean_orthogonality >= 0.60


def test_coupled_serial_chain_fallback():
    analyzer = SubtaskIndependenceAnalyzer(threshold=0.70)
    obj = TaskObjective(
        title="Sequential Compiler Pass",
        description="Lex, parse, optimize AST, and generate assembly sequentially.",
    )
    # Strongly coupled sequential tasks with chained dependencies
    s1 = SubtaskContract(
        subtask_id="s1",
        parent_task_id=obj.task_id,
        title="Lexical Analysis",
        query_or_instruction="Tokenize input stream into lexemes.",
        dependencies=[],
    )
    s2 = SubtaskContract(
        subtask_id="s2",
        parent_task_id=obj.task_id,
        title="AST Parser",
        query_or_instruction="Parse tokens into an Abstract Syntax Tree.",
        dependencies=["s1"],
    )
    s3 = SubtaskContract(
        subtask_id="s3",
        parent_task_id=obj.task_id,
        title="LLVM Codegen",
        query_or_instruction="Lower AST to LLVM intermediate representation.",
        dependencies=["s2"],
    )

    matrix = analyzer.analyze_matrix([s1, s2, s3])
    # Chained dependencies should not authorize flat PARALLEL_FAN_OUT
    assert matrix.gating_verdict != ExecutionStrategy.PARALLEL_FAN_OUT


def test_topological_wave_sorting():
    s1 = SubtaskContract(subtask_id="a", parent_task_id="t", title="A", query_or_instruction="A")
    s2 = SubtaskContract(subtask_id="b", parent_task_id="t", title="B", query_or_instruction="B")
    s3 = SubtaskContract(
        subtask_id="c",
        parent_task_id="t",
        title="C",
        query_or_instruction="C",
        dependencies=["a", "b"],
    )
    waves = topological_sort_waves([s1, s2, s3])
    assert len(waves) == 2
    assert {s.subtask_id for s in waves[0]} == {"a", "b"}
    assert {s.subtask_id for s in waves[1]} == {"c"}


def test_cyclic_dependency_rejection():
    s1 = SubtaskContract(
        subtask_id="x", parent_task_id="t", title="X", query_or_instruction="X", dependencies=["y"]
    )
    s2 = SubtaskContract(
        subtask_id="y", parent_task_id="t", title="Y", query_or_instruction="Y", dependencies=["x"]
    )
    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        topological_sort_waves([s1, s2])

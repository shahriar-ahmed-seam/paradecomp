"""Unit tests for ParaDecomp core models."""

import pytest
from pydantic import ValidationError

from paradecomp.core.models import (
    AggregatedOutput,
    DecompositionPlan,
    EvidenceItem,
    ExecutionStrategy,
    SubtaskContract,
    SubtaskExecutionResult,
    TaskObjective,
    TaskPriority,
)


def test_task_objective_defaults():
    obj = TaskObjective(
        title="Deep Research: Semiconductor Fabrication Advances",
        description=(
            "Comprehensive literature search over EUV lithography "
            "and gate-all-around architectures."
        ),
    )
    assert obj.task_id.startswith("task_")
    assert obj.priority == TaskPriority.MEDIUM
    assert obj.max_concurrency == 10
    assert obj.target_sources_count == 300


def test_subtask_contract_validation():
    contract = SubtaskContract(
        parent_task_id="task_123",
        title="High-NA EUV Optics Analysis",
        query_or_instruction="Extract numerical aperture and anamorphic magnification metrics.",
        dependencies=[],
        orthogonality_score=0.95,
    )
    assert contract.subtask_id.startswith("sub_")
    assert contract.dependencies == []
    assert contract.orthogonality_score == 0.95


def test_invalid_task_objective():
    with pytest.raises(ValidationError):
        TaskObjective(title="Hi", description="Too short")


def test_decomposition_plan_properties():
    sub1 = SubtaskContract(parent_task_id="t1", title="S1", query_or_instruction="Q1")
    sub2 = SubtaskContract(parent_task_id="t1", title="S2", query_or_instruction="Q2")
    plan = DecompositionPlan(
        task_id="t1",
        strategy=ExecutionStrategy.PARALLEL_FAN_OUT,
        subtasks=[sub1, sub2],
    )
    assert plan.total_subtasks == 2
    assert plan.is_parallel is True


def test_aggregated_output_serialization():
    evidence = EvidenceItem(
        source_uri="https://arxiv.org/abs/2401.0001",
        title="High-NA EUV Systems",
        snippet="Anamorphic magnification 4x/8x enables 0.55 NA.",
    )
    res = SubtaskExecutionResult(
        subtask_id="sub_1",
        worker_id="worker_0",
        evidence_sources=[evidence],
        duration_ms=45.2,
        tokens_used=120,
    )
    agg = AggregatedOutput(
        task_id="task_1",
        plan_id="plan_1",
        strategy_used=ExecutionStrategy.PARALLEL_FAN_OUT,
        total_subtasks=1,
        successful_subtasks=1,
        total_sources_gathered=1,
        wall_clock_duration_ms=45.2,
        coverage_per_second=22.1,
        synthesized_content="Summary of EUV systems.",
        subtask_results=[res],
    )
    json_data = agg.model_dump_json()
    assert "High-NA EUV Systems" in json_data

"""RFC canonical data models and schemas for ParaDecomp."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TaskPriority(str, Enum):
    """Priority level for task objectives."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionStrategy(str, Enum):
    """Gating decision for task execution architecture."""

    MONOLITHIC_SERIAL = "MONOLITHIC_SERIAL"
    PARALLEL_FAN_OUT = "PARALLEL_FAN_OUT"
    HYBRID_WAVE = "HYBRID_WAVE"


class CriticVerdict(str, Enum):
    """Deterministic verification verdict evaluated by critic."""

    VERIFIED = "VERIFIED"
    FLAGGED_DISCREPANCY = "FLAGGED_DISCREPANCY"
    REJECTED_HALLUCINATION = "REJECTED_HALLUCINATION"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceItem(BaseModel):
    """Unit of retrieved evidence or source observation."""

    source_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_uri: str = Field(..., description="Canonical URI or citation reference")
    title: str = Field(..., description="Document or source headline")
    snippet: str = Field(..., description="Extracted content text")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reliability_score: float = Field(default=1.0, ge=0.0, le=1.0)


class TaskObjective(BaseModel):
    """Top-level problem specification and operational constraints."""

    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    title: str = Field(..., min_length=3, description="Concise task title")
    description: str = Field(..., min_length=10, description="Full problem specification")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    context_payload: Dict[str, Any] = Field(default_factory=dict)
    max_concurrency: int = Field(default=10, ge=1, le=100)
    timeout_seconds: float = Field(default=60.0, gt=0.0)
    target_sources_count: int = Field(default=300, ge=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubtaskContract(BaseModel):
    """Strictly typed execution boundary for an isolated subtask."""

    subtask_id: str = Field(default_factory=lambda: f"sub_{uuid.uuid4().hex[:8]}")
    parent_task_id: str
    title: str
    query_or_instruction: str
    input_keys: List[str] = Field(default_factory=list)
    expected_output_schema: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(
        default_factory=list,
        description="IDs of antecedent subtasks. Empty implies full independence.",
    )
    timeout_seconds: float = Field(default=15.0, gt=0.0)
    max_retries: int = Field(default=2, ge=0)
    orthogonality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    allocated_tokens: int = Field(default=4096, gt=0)


class IndependenceMatrix(BaseModel):
    """Empirical mathematical assessment of subtask coupling and orthogonality."""

    subtask_ids: List[str]
    pairwise_overlap: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    pairwise_coupling: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    mean_orthogonality: float = Field(..., ge=0.0, le=1.0)
    gating_verdict: ExecutionStrategy
    justification: str

    @field_validator("mean_orthogonality")
    @classmethod
    def validate_bounds(cls, v: float) -> float:
        return round(v, 4)


class DecompositionPlan(BaseModel):
    """Decomposition blueprint produced by master orchestrator."""

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    task_id: str
    strategy: ExecutionStrategy
    subtasks: List[SubtaskContract] = Field(default_factory=list)
    concurrency_limit: int = Field(default=10, ge=1)
    independence_matrix: Optional[IndependenceMatrix] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_subtasks(self) -> int:
        return len(self.subtasks)

    @property
    def is_parallel(self) -> bool:
        return self.strategy == ExecutionStrategy.PARALLEL_FAN_OUT


class SubtaskExecutionResult(BaseModel):
    """Output payload from an individual worker agent execution."""

    subtask_id: str
    worker_id: str
    status: str = Field(default="SUCCESS", description="SUCCESS, FAILED, TIMEOUT")
    output_payload: Dict[str, Any] = Field(default_factory=dict)
    evidence_sources: List[EvidenceItem] = Field(default_factory=list)
    duration_ms: float = Field(default=0.0, ge=0.0)
    tokens_used: int = Field(default=0, ge=0)
    error_message: Optional[str] = None


class VerificationReport(BaseModel):
    """Evaluator and critic assessment report."""

    report_id: str = Field(default_factory=lambda: f"crit_{uuid.uuid4().hex[:8]}")
    verdict: CriticVerdict
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    contradictions_detected: List[str] = Field(default_factory=list)
    deduplicated_count: int = Field(default=0, ge=0)
    rechecked_sources_count: int = Field(default=0, ge=0)
    critic_notes: str = Field(default="")


class AggregatedOutput(BaseModel):
    """Final unified synthesis generated after scatter-gather reduction and critic pass."""

    task_id: str
    plan_id: str
    strategy_used: ExecutionStrategy
    total_subtasks: int
    successful_subtasks: int
    total_sources_gathered: int
    wall_clock_duration_ms: float
    coverage_per_second: float = Field(default=0.0)
    synthesized_content: str
    verification: Optional[VerificationReport] = None
    subtask_results: List[SubtaskExecutionResult] = Field(default_factory=list)

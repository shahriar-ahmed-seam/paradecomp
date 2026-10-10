"""ParaDecomp: High-Breadth Parallel Subtask Decomposition and Elastic
Scatter-Gather Concurrency Engine.
"""

__version__ = "0.1.0"
__author__ = "ParaDecomp Engineering Team"

from paradecomp.core.models import (
    AggregatedOutput,
    CriticVerdict,
    DecompositionPlan,
    SubtaskContract,
    SubtaskExecutionResult,
    TaskObjective,
)

__all__ = [
    "TaskObjective",
    "SubtaskContract",
    "DecompositionPlan",
    "SubtaskExecutionResult",
    "AggregatedOutput",
    "CriticVerdict",
]

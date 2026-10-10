"""Mathematical subtask independence analyzer and orthogonality gating engine."""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from paradecomp.core.models import (
    DecompositionPlan,
    ExecutionStrategy,
    IndependenceMatrix,
    SubtaskContract,
    TaskObjective,
)


def _tokenize(text: str) -> Set[str]:
    """Tokenize text into lowercase alphanumeric word tokens."""
    tokens = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    return set(tokens)


def compute_jaccard_similarity(tokens_a: Set[str], tokens_b: Set[str]) -> float:
    """Compute Jaccard similarity coefficient between two token sets."""
    if not tokens_a and not tokens_b:
        return 0.0
    intersection = len(tokens_a.intersection(tokens_b))
    union = len(tokens_a.union(tokens_b))
    return float(intersection) / float(union) if union > 0 else 0.0


def topological_sort_waves(subtasks: List[SubtaskContract]) -> List[List[SubtaskContract]]:
    """Group subtasks into independent topological waves for execution.

    Raises:
        ValueError: If a directed dependency cycle is detected.
    """
    id_map = {st.subtask_id: st for st in subtasks}
    in_degree: Dict[str, int] = {st.subtask_id: 0 for st in subtasks}
    dependents: Dict[str, List[str]] = {st.subtask_id: [] for st in subtasks}

    for st in subtasks:
        for dep in st.dependencies:
            if dep in id_map:
                in_degree[st.subtask_id] += 1
                dependents[dep].append(st.subtask_id)

    current_wave = [st for st in subtasks if in_degree[st.subtask_id] == 0]
    waves: List[List[SubtaskContract]] = []
    processed_count = 0

    while current_wave:
        waves.append(current_wave)
        processed_count += len(current_wave)
        next_wave_ids: List[str] = []

        for st in current_wave:
            for dep_id in dependents[st.subtask_id]:
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    next_wave_ids.append(dep_id)

        current_wave = [id_map[nid] for nid in next_wave_ids]

    if processed_count != len(subtasks):
        raise ValueError("Cyclic dependency detected in subtask graph")

    return waves


class SubtaskIndependenceAnalyzer:
    """Evaluates semantic orthogonality and mathematical independence between subtasks."""

    def __init__(self, alpha: float = 0.5, threshold: float = 0.70):
        """Initialize analyzer.

        Args:
            alpha: Weight balancing context overlap (alpha) vs coupling (1 - alpha).
            threshold: Minimum mean orthogonality required to authorize PARALLEL_FAN_OUT.
        """
        self.alpha = max(0.0, min(1.0, alpha))
        self.threshold = threshold

    def compute_overlap(self, t1: SubtaskContract, t2: SubtaskContract) -> float:
        """Estimate state and context overlap between two subtasks."""
        text1 = f"{t1.title} {t1.query_or_instruction} {' '.join(t1.input_keys)}"
        text2 = f"{t2.title} {t2.query_or_instruction} {' '.join(t2.input_keys)}"
        return compute_jaccard_similarity(_tokenize(text1), _tokenize(text2))

    def compute_coupling(self, t1: SubtaskContract, t2: SubtaskContract) -> float:
        """Compute causal dependency coupling between two subtasks."""
        # Direct causal dependency
        if t1.subtask_id in t2.dependencies or t2.subtask_id in t1.dependencies:
            return 1.0

        # Shared antecedents
        deps1 = set(t1.dependencies)
        deps2 = set(t2.dependencies)
        if deps1 and deps2:
            shared = deps1.intersection(deps2)
            total = deps1.union(deps2)
            return float(len(shared)) / float(len(total))

        return 0.0

    def compute_orthogonality(self, t1: SubtaskContract, t2: SubtaskContract) -> float:
        """Formulate pairwise orthogonality O(T1, T2)."""
        overlap = self.compute_overlap(t1, t2)
        coupling = self.compute_coupling(t1, t2)
        ortho = 1.0 - (self.alpha * overlap + (1.0 - self.alpha) * coupling)
        return max(0.0, min(1.0, ortho))

    def analyze_matrix(self, subtasks: List[SubtaskContract]) -> IndependenceMatrix:
        """Construct the full pairwise independence matrix across subtasks."""
        if not subtasks:
            return IndependenceMatrix(
                subtask_ids=[],
                mean_orthogonality=1.0,
                gating_verdict=ExecutionStrategy.MONOLITHIC_SERIAL,
                justification="Empty subtask set; defaulting to serial monolith.",
            )

        n = len(subtasks)
        ids = [st.subtask_id for st in subtasks]
        pairwise_overlap: Dict[str, Dict[str, float]] = {sid: {} for sid in ids}
        pairwise_coupling: Dict[str, Dict[str, float]] = {sid: {} for sid in ids}
        pairwise_ortho: List[float] = []

        for i in range(n):
            sid_i = ids[i]
            for j in range(n):
                sid_j = ids[j]
                if i == j:
                    pairwise_overlap[sid_i][sid_j] = 1.0
                    pairwise_coupling[sid_i][sid_j] = 1.0
                else:
                    ov = self.compute_overlap(subtasks[i], subtasks[j])
                    cp = self.compute_coupling(subtasks[i], subtasks[j])
                    ortho = 1.0 - (self.alpha * ov + (1.0 - self.alpha) * cp)
                    pairwise_overlap[sid_i][sid_j] = round(ov, 4)
                    pairwise_coupling[sid_i][sid_j] = round(cp, 4)
                    if i < j:
                        pairwise_ortho.append(ortho)

        mean_ortho = sum(pairwise_ortho) / len(pairwise_ortho) if pairwise_ortho else 1.0

        # Check for dependency cycles or waves
        try:
            waves = topological_sort_waves(subtasks)
        except ValueError as exc:
            return IndependenceMatrix(
                subtask_ids=ids,
                pairwise_overlap=pairwise_overlap,
                pairwise_coupling=pairwise_coupling,
                mean_orthogonality=0.0,
                gating_verdict=ExecutionStrategy.MONOLITHIC_SERIAL,
                justification=f"Dependency cycle detected ({exc}); forced serial recovery.",
            )

        if len(waves) == 1 and mean_ortho >= self.threshold:
            verdict = ExecutionStrategy.PARALLEL_FAN_OUT
            justification = (
                f"Subtasks are mutually independent with mean orthogonality {mean_ortho:.3f} >= "
                f"{self.threshold:.2f} and zero cross-dependencies. Parallel fan-out authorized."
            )
        elif len(waves) > 1 and any(len(w) > 1 for w in waves):
            verdict = ExecutionStrategy.HYBRID_WAVE
            justification = (
                f"Multi-wave dependency graph detected ({len(waves)} waves). "
                f"Independent wave tiers will execute in concurrent scatter-gather batches."
            )
        else:
            verdict = ExecutionStrategy.MONOLITHIC_SERIAL
            justification = (
                f"High subtask coupling or low orthogonality ({mean_ortho:.3f} < "
                f"{self.threshold:.2f}). Orchestration overhead outweighs parallel speedup. "
                "Executing as unified single-agent monolith to preserve full context fidelity."
            )

        return IndependenceMatrix(
            subtask_ids=ids,
            pairwise_overlap=pairwise_overlap,
            pairwise_coupling=pairwise_coupling,
            mean_orthogonality=mean_ortho,
            gating_verdict=verdict,
            justification=justification,
        )

    def decompose(
        self,
        objective: TaskObjective,
        facets: List[Tuple[str, str]],
        dependencies_map: Dict[int, List[int]] | None = None,
    ) -> DecompositionPlan:
        """Generate a complete DecompositionPlan for a given objective.

        Args:
            objective: The root problem objective.
            facets: List of (title, instruction) tuples to decompose into.
            dependencies_map: Optional map of facet index -> list of dependency facet indices.
        """
        dependencies_map = dependencies_map or {}
        subtasks: List[SubtaskContract] = []

        # Create subtask contracts
        for idx, (title, instruction) in enumerate(facets):
            dep_indices = dependencies_map.get(idx, [])
            dep_ids = [f"sub_{objective.task_id}_{dep_idx}" for dep_idx in dep_indices]
            subtask = SubtaskContract(
                subtask_id=f"sub_{objective.task_id}_{idx}",
                parent_task_id=objective.task_id,
                title=title,
                query_or_instruction=instruction,
                dependencies=dep_ids,
                timeout_seconds=objective.timeout_seconds / max(1, len(facets)),
            )
            subtasks.append(subtask)

        matrix = self.analyze_matrix(subtasks)

        # Update each subtask orthogonality score
        for st in subtasks:
            other_scores = [
                matrix.pairwise_overlap.get(st.subtask_id, {}).get(other.subtask_id, 0.0)
                for other in subtasks
                if other.subtask_id != st.subtask_id
            ]
            st.orthogonality_score = (
                1.0 - (sum(other_scores) / len(other_scores)) if other_scores else 1.0
            )

        return DecompositionPlan(
            task_id=objective.task_id,
            strategy=matrix.gating_verdict,
            subtasks=subtasks,
            concurrency_limit=objective.max_concurrency,
            independence_matrix=matrix,
        )

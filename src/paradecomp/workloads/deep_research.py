"""High-breadth Deep Research workload engine scaling from ~30 to ~300 sources."""

from __future__ import annotations

import asyncio
from typing import Callable, List, Optional

from pydantic import BaseModel, Field

from paradecomp.analyzer.independence import SubtaskIndependenceAnalyzer
from paradecomp.core.models import (
    AggregatedOutput,
    DecompositionPlan,
    EvidenceItem,
    SubtaskContract,
    SubtaskExecutionResult,
    TaskObjective,
)
from paradecomp.critic.verifier import CriticGatedVerifier
from paradecomp.runtime.scatter_gather import ElasticScatterGatherRuntime


class ResearchFacet(BaseModel):
    """Sub-topic or exploration facet of a research domain."""

    facet_id: str
    title: str
    query: str
    expected_sources: int = Field(default=30, ge=1)


class DeepResearchEngine:
    """Master research engine orchestrating high-breadth parallel decomposition."""

    def __init__(
        self,
        runtime: Optional[ElasticScatterGatherRuntime] = None,
        verifier: Optional[CriticGatedVerifier] = None,
        analyzer: Optional[SubtaskIndependenceAnalyzer] = None,
    ) -> None:
        self.runtime = runtime or ElasticScatterGatherRuntime(concurrency_limit=10)
        self.verifier = verifier or CriticGatedVerifier(min_sources_threshold=20)
        self.analyzer = analyzer or SubtaskIndependenceAnalyzer(threshold=0.65)

    def prepare_plan(
        self,
        objective_title: str,
        facets: List[ResearchFacet],
    ) -> DecompositionPlan:
        """Partition research query into orthogonal subtask contracts."""
        task_obj = TaskObjective(
            title=objective_title,
            description=f"High-breadth deep research investigation across {len(facets)} facets.",
            target_sources_count=sum(f.expected_sources for f in facets),
            max_concurrency=len(facets),
        )
        facet_tuples = [(f.title, f.query) for f in facets]
        plan = self.analyzer.decompose(task_obj, facet_tuples)
        return plan

    async def run(
        self,
        objective_title: str,
        facets: List[ResearchFacet],
        worker_provider: Optional[Callable[[SubtaskContract, int], List[EvidenceItem]]] = None,
    ) -> AggregatedOutput:
        """Execute high-breadth deep research and verify with critic model."""
        plan = self.prepare_plan(objective_title, facets)

        # Worker execution implementation
        async def research_worker(st: SubtaskContract) -> SubtaskExecutionResult:
            # Match facet
            facet_idx = int(st.subtask_id.split("_")[-1])
            facet = facets[facet_idx] if facet_idx < len(facets) else facets[0]

            if worker_provider:
                evidence = worker_provider(st, facet.expected_sources)
            else:
                # Default synthetic research generator for deterministic benchmarking
                await asyncio.sleep(0.02)
                evidence = [
                    EvidenceItem(
                        source_uri=f"https://research.archive.org/{st.subtask_id}/source_{i}",
                        title=f"{facet.title} - Investigation Vector {i:02d}",
                        snippet=(
                            f"Empirical evidence for {facet.title}: factor {i} demonstrates "
                            "significant correlation with high-throughput scaling."
                        ),
                        reliability_score=0.95,
                    )
                    for i in range(facet.expected_sources)
                ]

            return SubtaskExecutionResult(
                subtask_id=st.subtask_id,
                worker_id="",
                status="SUCCESS",
                output_payload={
                    "summary": (
                        f"Synthesized findings for {facet.title} across {len(evidence)} citations."
                    )
                },
                evidence_sources=evidence,
                tokens_used=len(evidence) * 45,
            )

        aggregated = await self.runtime.execute_plan(plan, research_worker)
        self.verifier.evaluate(aggregated, target_sources=plan.total_subtasks * 20)
        return aggregated

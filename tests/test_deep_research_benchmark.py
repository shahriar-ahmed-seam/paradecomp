"""Unit tests for DeepResearchEngine and BenchmarkRunner."""

import asyncio

from paradecomp.benchmarks.runner import BenchmarkRunner
from paradecomp.core.models import CriticVerdict
from paradecomp.workloads.deep_research import (
    DeepResearchEngine,
    ResearchFacet,
)


def test_deep_research_engine_execution():
    async def _test():
        engine = DeepResearchEngine()
        facets = [
            ResearchFacet(
                facet_id="f1",
                title="Lithography Optics",
                query="High-NA anamorphic mirrors",
                expected_sources=10,
            ),
            ResearchFacet(
                facet_id="f2",
                title="GAA Nanosheets",
                query="Inner spacer etch selectivity",
                expected_sources=10,
            ),
            ResearchFacet(
                facet_id="f3",
                title="Direct Hybrid Bonding",
                query="Cu-Cu pad alignment tolerances",
                expected_sources=10,
            ),
        ]
        res = await engine.run(
            objective_title="Advanced Packaging and Nanosheet Tech",
            facets=facets,
        )
        assert res.total_subtasks == 3
        assert res.successful_subtasks == 3
        assert res.total_sources_gathered == 30
        assert res.verification is not None
        assert res.verification.verdict in [CriticVerdict.VERIFIED, CriticVerdict.INCONCLUSIVE]

    asyncio.run(_test())


def test_benchmark_runner():
    async def _test():
        runner = BenchmarkRunner()
        report = await runner.run(num_facets=5, sources_per_facet=20, simulated_io_ms=10.0)
        assert report.num_subtasks == 5
        assert report.serial_sources_pulled == 30
        assert report.parallel_sources_pulled == 100
        assert report.breadth_multiplier > 3.0
        assert report.parallel_sources_per_second > 0

    asyncio.run(_test())

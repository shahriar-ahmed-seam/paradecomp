"""Unit tests for ElasticScatterGatherRuntime, RateLimiter, and EventBus."""

import asyncio
import time

from paradecomp.core.models import (
    DecompositionPlan,
    EvidenceItem,
    ExecutionStrategy,
    SubtaskContract,
    SubtaskExecutionResult,
)
from paradecomp.runtime.events import EventBus, RuntimeEvent, RuntimeEventType
from paradecomp.runtime.scatter_gather import ElasticScatterGatherRuntime, RateLimiter


def test_event_bus():
    async def _test():
        bus = EventBus()
        received = []

        def on_event(ev: RuntimeEvent):
            received.append(ev.event_type)

        bus.subscribe(on_event)
        await bus.emit(RuntimeEvent(event_type=RuntimeEventType.TASK_SPAWNED, task_id="t1"))
        assert len(received) == 1
        assert received[0] == RuntimeEventType.TASK_SPAWNED

    asyncio.run(_test())


def test_rate_limiter():
    async def _test():
        limiter = RateLimiter(requests_per_minute=6000)
        start = time.monotonic()
        await limiter.acquire(1.0)
        assert time.monotonic() - start < 1.0

    asyncio.run(_test())


def test_parallel_scatter_gather_execution():
    async def _test():
        runtime = ElasticScatterGatherRuntime(concurrency_limit=5)

        async def mock_worker(st: SubtaskContract) -> SubtaskExecutionResult:
            await asyncio.sleep(0.04)
            evidence = [
                EvidenceItem(
                    source_uri=f"https://source.dev/{st.subtask_id}_{i}",
                    title=f"Source {i} for {st.title}",
                    snippet=f"Extracted payload {i}",
                )
                for i in range(5)
            ]
            return SubtaskExecutionResult(
                subtask_id=st.subtask_id,
                worker_id="",
                status="SUCCESS",
                output_payload={"summary": f"Findings for {st.title}"},
                evidence_sources=evidence,
                tokens_used=150,
            )

        subtasks = [
            SubtaskContract(
                subtask_id=f"st_{i}",
                parent_task_id="task_p",
                title=f"Facet {i}",
                query_or_instruction=f"Query {i}",
            )
            for i in range(5)
        ]
        plan = DecompositionPlan(
            task_id="task_p",
            strategy=ExecutionStrategy.PARALLEL_FAN_OUT,
            subtasks=subtasks,
            concurrency_limit=5,
        )

        start = time.monotonic()
        output = await runtime.execute_plan(plan, mock_worker)
        duration = time.monotonic() - start

        # 5 tasks of 40ms in parallel should take ~40-80ms, well below serial 200ms
        assert duration < 0.18
        assert output.total_sources_gathered == 25
        assert output.successful_subtasks == 5
        assert output.coverage_per_second > 0

    asyncio.run(_test())


def test_worker_timeout_handling():
    async def _test():
        runtime = ElasticScatterGatherRuntime(concurrency_limit=2)

        async def hanging_worker(st: SubtaskContract) -> SubtaskExecutionResult:
            await asyncio.sleep(0.5)
            return SubtaskExecutionResult(
                subtask_id=st.subtask_id,
                worker_id="",
                status="SUCCESS",
                output_payload={},
            )

        st = SubtaskContract(
            subtask_id="st_slow",
            parent_task_id="t",
            title="Slow subtask",
            query_or_instruction="Do work",
            timeout_seconds=0.04,
            max_retries=0,
        )
        res = await runtime.execute_subtask(st, hanging_worker, "worker_0")
        assert res.status == "FAILED"
        assert "timed out" in (res.error_message or "").lower()

    asyncio.run(_test())

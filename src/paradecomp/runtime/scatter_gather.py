"""Elastic scatter-gather concurrency runtime and bounded worker pool."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from paradecomp.analyzer.independence import topological_sort_waves
from paradecomp.core.models import (
    AggregatedOutput,
    DecompositionPlan,
    ExecutionStrategy,
    SubtaskContract,
    SubtaskExecutionResult,
)
from paradecomp.runtime.events import (
    EventBus,
    RuntimeEvent,
    RuntimeEventType,
)

WorkerCallable = Callable[[SubtaskContract], Awaitable[SubtaskExecutionResult]]


class RateLimiter:
    """Asynchronous token-bucket rate limiter for API calls."""

    def __init__(self, requests_per_minute: int = 600) -> None:
        self.capacity = float(requests_per_minute)
        self.tokens = float(requests_per_minute)
        self.fill_rate = float(requests_per_minute) / 60.0
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """Acquire tokens, sleeping if rate limit is exceeded."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)

            if self.tokens < tokens:
                deficit = tokens - self.tokens
                wait_time = deficit / self.fill_rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= tokens


class ElasticScatterGatherRuntime:
    """Bounded-concurrency scatter-gather orchestration engine."""

    def __init__(
        self,
        concurrency_limit: int = 10,
        rate_limiter: Optional[RateLimiter] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.concurrency_limit = max(1, concurrency_limit)
        self.semaphore = asyncio.Semaphore(self.concurrency_limit)
        self.rate_limiter = rate_limiter or RateLimiter(requests_per_minute=3000)
        self.event_bus = event_bus or EventBus()

    async def execute_subtask(
        self,
        subtask: SubtaskContract,
        worker_fn: WorkerCallable,
        worker_id: str,
    ) -> SubtaskExecutionResult:
        """Execute an individual subtask with bounded concurrency, retries, and timeout."""
        await self.rate_limiter.acquire(1.0)
        await self.event_bus.emit(
            RuntimeEvent(
                event_type=RuntimeEventType.WORKER_STARTED,
                task_id=subtask.parent_task_id,
                subtask_id=subtask.subtask_id,
                worker_id=worker_id,
                details={"title": subtask.title},
            )
        )

        attempts = 0
        max_attempts = max(1, subtask.max_retries + 1)
        last_error = ""

        while attempts < max_attempts:
            attempts += 1
            start_time = time.monotonic()
            try:
                async with self.semaphore:
                    result = await asyncio.wait_for(
                        worker_fn(subtask),
                        timeout=subtask.timeout_seconds,
                    )
                duration_ms = (time.monotonic() - start_time) * 1000.0
                result.duration_ms = round(duration_ms, 2)
                result.worker_id = worker_id
                await self.event_bus.emit(
                    RuntimeEvent(
                        event_type=RuntimeEventType.WORKER_COMPLETED,
                        task_id=subtask.parent_task_id,
                        subtask_id=subtask.subtask_id,
                        worker_id=worker_id,
                        details={
                            "duration_ms": duration_ms,
                            "sources_count": len(result.evidence_sources),
                        },
                    )
                )
                return result

            except asyncio.TimeoutError:
                last_error = f"Execution timed out after {subtask.timeout_seconds}s"
                await self.event_bus.emit(
                    RuntimeEvent(
                        event_type=RuntimeEventType.WORKER_TIMEOUT,
                        task_id=subtask.parent_task_id,
                        subtask_id=subtask.subtask_id,
                        worker_id=worker_id,
                        details={"attempt": attempts, "error": last_error},
                    )
                )
            except Exception as exc:
                last_error = f"Worker exception: {str(exc)}"
                await self.event_bus.emit(
                    RuntimeEvent(
                        event_type=RuntimeEventType.WORKER_FAILED,
                        task_id=subtask.parent_task_id,
                        subtask_id=subtask.subtask_id,
                        worker_id=worker_id,
                        details={"attempt": attempts, "error": last_error},
                    )
                )

        # Retries exhausted
        duration_ms = (time.monotonic() - start_time) * 1000.0
        return SubtaskExecutionResult(
            subtask_id=subtask.subtask_id,
            worker_id=worker_id,
            status="FAILED",
            output_payload={},
            evidence_sources=[],
            duration_ms=round(duration_ms, 2),
            tokens_used=0,
            error_message=last_error,
        )

    async def execute_plan(
        self,
        plan: DecompositionPlan,
        worker_fn: WorkerCallable,
    ) -> AggregatedOutput:
        """Execute a full decomposition plan and aggregate worker outputs."""
        await self.event_bus.emit(
            RuntimeEvent(
                event_type=RuntimeEventType.TASK_SPAWNED,
                task_id=plan.task_id,
                details={
                    "strategy": plan.strategy.value,
                    "subtasks_count": plan.total_subtasks,
                    "concurrency_limit": self.concurrency_limit,
                },
            )
        )

        overall_start = time.monotonic()
        results: List[SubtaskExecutionResult] = []

        if plan.strategy == ExecutionStrategy.PARALLEL_FAN_OUT:
            # Full scatter-gather: launch all subtasks concurrently
            tasks = [
                self.execute_subtask(
                    subtask=st,
                    worker_fn=worker_fn,
                    worker_id=f"worker_{idx % self.concurrency_limit:02d}",
                )
                for idx, st in enumerate(plan.subtasks)
            ]
            results = await asyncio.gather(*tasks)

        elif plan.strategy == ExecutionStrategy.HYBRID_WAVE:
            # Topological wave dispatch
            waves = topological_sort_waves(plan.subtasks)
            for wave in waves:
                wave_tasks = [
                    self.execute_subtask(
                        subtask=st,
                        worker_fn=worker_fn,
                        worker_id=f"wave_worker_{idx % self.concurrency_limit:02d}",
                    )
                    for idx, st in enumerate(wave)
                ]
                wave_results = await asyncio.gather(*wave_tasks)
                results.extend(wave_results)

        else:
            # MONOLITHIC_SERIAL: Execute sequentially in strict order
            for idx, st in enumerate(plan.subtasks):
                res = await self.execute_subtask(
                    subtask=st,
                    worker_fn=worker_fn,
                    worker_id="serial_worker_00",
                )
                results.append(res)

        wall_clock_ms = (time.monotonic() - overall_start) * 1000.0

        # Aggregation reduction phase
        successful_subtasks = sum(1 for r in results if r.status == "SUCCESS")
        all_sources: List[Dict[str, Any]] = []
        synthesized_parts: List[str] = []

        for r in results:
            if r.status == "SUCCESS":
                for src in r.evidence_sources:
                    all_sources.append(src.model_dump())
                summary = r.output_payload.get("summary", "")
                if summary:
                    synthesized_parts.append(summary)

        total_sources = len(all_sources)
        duration_s = max(0.001, wall_clock_ms / 1000.0)
        coverage_per_sec = total_sources / duration_s

        synthesized_content = (
            "\n\n".join(synthesized_parts)
            if synthesized_parts
            else f"Gathered {total_sources} evidence items across {successful_subtasks} subtasks."
        )

        aggregated = AggregatedOutput(
            task_id=plan.task_id,
            plan_id=plan.plan_id,
            strategy_used=plan.strategy,
            total_subtasks=len(plan.subtasks),
            successful_subtasks=successful_subtasks,
            total_sources_gathered=total_sources,
            wall_clock_duration_ms=round(wall_clock_ms, 2),
            coverage_per_second=round(coverage_per_sec, 2),
            synthesized_content=synthesized_content,
            subtask_results=list(results),
        )

        await self.event_bus.emit(
            RuntimeEvent(
                event_type=RuntimeEventType.GATHER_COMPLETED,
                task_id=plan.task_id,
                details={
                    "total_sources": total_sources,
                    "wall_clock_ms": wall_clock_ms,
                    "coverage_per_sec": coverage_per_sec,
                },
            )
        )

        return aggregated

"""Event bus and streaming telemetry models for scatter-gather execution."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List

from pydantic import BaseModel, Field


class RuntimeEventType(str, Enum):
    """Lifecycle event types emitted by scatter-gather engine."""

    TASK_SPAWNED = "TASK_SPAWNED"
    WORKER_STARTED = "WORKER_STARTED"
    WORKER_COMPLETED = "WORKER_COMPLETED"
    WORKER_FAILED = "WORKER_FAILED"
    WORKER_TIMEOUT = "WORKER_TIMEOUT"
    GATHER_COMPLETED = "GATHER_COMPLETED"


class RuntimeEvent(BaseModel):
    """Immutable telemetry event record."""

    event_type: RuntimeEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    task_id: str
    subtask_id: str = ""
    worker_id: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class EventBus:
    """Asynchronous pub/sub event bus for streaming runtime telemetry."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[RuntimeEvent], Any]] = []
        self._history: List[RuntimeEvent] = []

    def subscribe(self, callback: Callable[[RuntimeEvent], Any]) -> None:
        """Register a callback for streaming events."""
        self._subscribers.append(callback)

    async def emit(self, event: RuntimeEvent) -> None:
        """Emit an event to all subscribers and append to history."""
        self._history.append(event)
        for sub in self._subscribers:
            try:
                res = sub(event)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                # Event subscriber failures should not crash engine
                pass

    @property
    def history(self) -> List[RuntimeEvent]:
        """Return history of emitted events."""
        return list(self._history)

    def clear(self) -> None:
        """Clear event history."""
        self._history.clear()

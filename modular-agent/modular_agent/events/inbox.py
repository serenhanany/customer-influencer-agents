"""Module 3 — the injection point for world events.

``EventInbox`` is a thread-safe queue plus an optional subscriber hook. External
producers call :meth:`inject`; the agent loop pulls with :meth:`get` /
:meth:`get_nowait`. Nothing about the producer leaks into the agent and vice
versa — they only share ``WorldEvent`` objects.
"""

from __future__ import annotations

import queue
from typing import Callable

from .event import WorldEvent


class EventInbox:
    def __init__(self) -> None:
        self._queue: "queue.Queue[WorldEvent]" = queue.Queue()
        self._subscribers: list[Callable[[WorldEvent], None]] = []

    def inject(self, event: WorldEvent) -> None:
        """Push an event in. Safe to call from any thread/producer."""
        self._queue.put(event)
        for cb in list(self._subscribers):
            try:
                cb(event)
            except Exception:  # a bad subscriber must not break injection
                pass

    def subscribe(self, callback: Callable[[WorldEvent], None]) -> None:
        """Register a fire-and-forget hook run on every injected event."""
        self._subscribers.append(callback)

    def get(self, block: bool = True, timeout: float | None = None) -> WorldEvent:
        return self._queue.get(block=block, timeout=timeout)

    def get_nowait(self) -> WorldEvent:
        return self._queue.get_nowait()

    def empty(self) -> bool:
        return self._queue.empty()

    def __len__(self) -> int:
        return self._queue.qsize()

"""Module 4b — memory bundle.

Groups the memory layers an agent uses into one object. ``working`` and
``episodic`` are always on; ``semantic`` is opt-in (defaults to ``None`` and is
only wired up when a developer enables the chromadb-backed store).
"""

from __future__ import annotations

from typing import Any

from .episodic import EpisodicMemory
from .retrieval import RetrievalPolicy
from .working import WorkingMemory


class MemoryBundle:
    def __init__(
        self,
        working: WorkingMemory | None = None,
        episodic: EpisodicMemory | None = None,
        semantic: Any | None = None,
        retrieval: RetrievalPolicy | None = None,
    ) -> None:
        self.working = working or WorkingMemory()
        self.episodic = episodic or EpisodicMemory()
        self.semantic = semantic  # opt-in long-term store (see memory/semantic.py)
        self.retrieval = retrieval or RetrievalPolicy()

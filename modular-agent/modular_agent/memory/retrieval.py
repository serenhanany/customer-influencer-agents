"""Module 4b — retrieval policy.

Decides what memory gets pulled into a given invoke. Kept deliberately simple:
the most recent episodic records, plus (when a semantic store is enabled) the
top-k semantically similar snippets. A developer can subclass and override
``build_context`` to change what the LLM sees.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .bundle import MemoryBundle
    from ..events.event import WorldEvent


class RetrievalPolicy:
    def __init__(self, episodic_n: int = 5, semantic_k: int = 3) -> None:
        self.episodic_n = episodic_n
        self.semantic_k = semantic_k

    def build_context(self, event: "WorldEvent", memory: "MemoryBundle") -> str:
        parts: list[str] = []

        recent = memory.episodic.render_recent(self.episodic_n)
        if recent:
            parts.append("Recent history:\n" + recent)

        if memory.semantic is not None:
            try:
                hits: list[Any] = memory.semantic.search(event.render(), k=self.semantic_k)
                if hits:
                    parts.append("Relevant recollections:\n" + "\n".join(f"- {h}" for h in hits))
            except Exception:
                pass  # semantic memory is best-effort context, never fatal

        return "\n\n".join(parts)

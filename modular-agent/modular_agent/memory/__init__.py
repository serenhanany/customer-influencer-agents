from .bundle import MemoryBundle
from .episodic import EpisodicMemory, EpisodicRecord
from .retrieval import RetrievalPolicy
from .working import WorkingMemory

__all__ = [
    "MemoryBundle",
    "WorkingMemory",
    "EpisodicMemory",
    "EpisodicRecord",
    "RetrievalPolicy",
    "SemanticMemory",
]


def __getattr__(name: str):
    # Lazy so importing `modular_agent.memory` doesn't require chromadb.
    if name == "SemanticMemory":
        from .semantic import SemanticMemory

        return SemanticMemory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

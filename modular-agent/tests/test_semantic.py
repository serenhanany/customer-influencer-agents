"""Module 4b — semantic memory, exercised fully offline.

Uses a deterministic fake embedder so the test needs no model download and no
network. Skips cleanly if chromadb isn't installed.
"""

import pytest

chromadb = pytest.importorskip("chromadb")

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings  # noqa: E402

from modular_agent.memory import SemanticMemory  # noqa: E402


class FakeEmbedder(EmbeddingFunction):
    """Tiny deterministic embedder — no network, no model."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return [[float(len(t)), float(sum(map(ord, t)) % 97), 1.0] for t in input]

    @staticmethod
    def name() -> str:
        return "fake"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config) -> "FakeEmbedder":
        return FakeEmbedder()


def test_requires_embedder_or_explicit_optin():
    with pytest.raises(ValueError):
        SemanticMemory()  # no embedder, no opt-in -> refuse (avoids silent download)


def test_add_search_count_offline():
    mem = SemanticMemory(embedding_function=FakeEmbedder())
    assert mem.count() == 0
    assert mem.search("anything") == []  # empty store returns nothing

    mem.add("the tuna is fine", metadata={"kind": "note"})
    mem.add("contamination rumor spreading fast")
    assert mem.count() == 2

    hits = mem.search("rumor about contamination", k=1)
    assert len(hits) == 1
    assert isinstance(hits[0], str)

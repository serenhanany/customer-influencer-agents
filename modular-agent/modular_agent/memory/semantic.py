"""Module 4b — semantic (long-term) memory.

An opt-in, chromadb-backed store the agent can write recollections to and
retrieve by similarity across invokes. It is **not** wired into an agent by
default — a developer constructs it explicitly and passes it to a
``MemoryBundle``.

Network policy (deliberate):
- The vector store runs fully **locally** (in-memory, or on-disk via ``path``).
- Embeddings are pluggable. You must either pass your own ``embedding_function``
  (keeps everything offline) **or** explicitly set ``use_default_embedder=True``
  to use chromadb's built-in embedder, which downloads a ~80MB model on first
  use. Nothing hits the network unless you opt in.

``chromadb`` is imported lazily so the rest of the package stays importable
without it installed.
"""

from __future__ import annotations

import uuid
from typing import Any


class SemanticMemory:
    def __init__(
        self,
        collection: str = "agent_memory",
        path: str | None = None,
        embedding_function: Any | None = None,
        use_default_embedder: bool = False,
    ) -> None:
        if embedding_function is None and not use_default_embedder:
            raise ValueError(
                "SemanticMemory needs an embedding_function (offline), or pass "
                "use_default_embedder=True to use chromadb's built-in embedder "
                "(downloads a ~80MB model on first use)."
            )

        import chromadb

        self._client = chromadb.PersistentClient(path=path) if path else chromadb.EphemeralClient()
        kwargs: dict[str, Any] = {}
        if embedding_function is not None:
            kwargs["embedding_function"] = embedding_function  # else chromadb's default (downloads)
        self._collection = self._client.get_or_create_collection(collection, **kwargs)

    def add(self, text: str, metadata: dict | None = None, id: str | None = None) -> str:
        """Store a snippet; returns its id."""
        _id = id or uuid.uuid4().hex
        add_kwargs: dict[str, Any] = {"documents": [text], "ids": [_id]}
        if metadata:
            add_kwargs["metadatas"] = [metadata]
        self._collection.add(**add_kwargs)
        return _id

    def search(self, query: str, k: int = 3) -> list[str]:
        """Return up to ``k`` most similar stored snippets."""
        n = self.count()
        if n == 0:
            return []
        result = self._collection.query(query_texts=[query], n_results=min(k, n))
        docs = result.get("documents") or [[]]
        return docs[0]

    def count(self) -> int:
        return self._collection.count()

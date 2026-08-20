import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document

from services.embedding_service import EmbeddingService


@dataclass
class MemoryConfig:
    persist_directory: str = "./chroma_ceo_memory_db"
    collection_name: str = "ceo_long_term_memory"


@dataclass
class MemoryRecord:
    """One full chat() run: the event handled, how it was handled, and how it ended."""
    event: str
    plan: list[str]
    step_results: list[dict[str, Any]]
    final_summary: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MemoryStore:
    """Long-term episodic memory for the CEO agent, backed by a dedicated Chroma collection.

    Kept separate from DocumentStore: that store splits files into chunks for
    passage retrieval, but a memory record is one indivisible event -- splitting
    it would let recall return half a decision divorced from its outcome.
    """

    def __init__(
            self,
            embedding_service: EmbeddingService,
            config: MemoryConfig = MemoryConfig(),
    ) -> None:
        self._store = Chroma(
            collection_name=config.collection_name,
            embedding_function=embedding_service.get_model(),
            persist_directory=config.persist_directory,
            collection_metadata={"hnsw:space": "cosine"},
        )

    def remember(self, record: MemoryRecord) -> None:
        """Embeds and persists one run so future events can recall it."""
        page_content = (
            f"Event: {record.event}\n"
            f"Plan: {json.dumps(record.plan)}\n"
            f"Final decision: {record.final_summary}"
        )
        document = Document(
            page_content=page_content,
            metadata={
                "event": record.event,
                "plan": json.dumps(record.plan),
                "step_results": json.dumps(record.step_results, default=str),
                "final_summary": record.final_summary,
                "timestamp": record.timestamp,
            },
        )
        self._store.add_documents([document])

    def recall(self, query: str, top_k: int = 3) -> list[MemoryRecord]:
        """Returns the top_k memory records most similar to query, best first."""
        results = self._store.similarity_search_with_score(query, k=top_k)
        records = []
        for doc, _score in results:
            meta = doc.metadata
            records.append(MemoryRecord(
                event=meta.get("event", ""),
                plan=json.loads(meta.get("plan", "[]")),
                step_results=json.loads(meta.get("step_results", "[]")),
                final_summary=meta.get("final_summary", ""),
                timestamp=meta.get("timestamp", ""),
            ))
        return records

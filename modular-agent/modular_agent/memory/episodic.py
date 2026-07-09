"""Module 4b — episodic memory.

An append-only log of what the agent perceived and did: events it reacted to,
tool actions it took, and responses it produced. This doubles as the project's
"decision logging" surface. Optionally mirrors records to a JSONL file so a run
can be inspected or replayed after the fact.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EpisodicRecord:
    kind: str  # "event" | "action" | "response"
    data: dict[str, Any]
    ts: str = field(default_factory=_now_iso)


class EpisodicMemory:
    def __init__(self, path: str | None = None) -> None:
        self.path = path
        self._records: list[EpisodicRecord] = []

    # --- writers -------------------------------------------------------
    def record_event(self, event: Any) -> None:
        self._add("event", {"id": getattr(event, "id", None), "type": getattr(event, "type", None),
                            "source": getattr(event, "source", None), "payload": getattr(event, "payload", {})})

    def record_action(self, tool: str, tool_input: Any, observation: Any) -> None:
        self._add("action", {"tool": tool, "input": _safe(tool_input), "observation": _safe(observation)})

    def record_response(self, event_id: str | None, output: str) -> None:
        self._add("response", {"event_id": event_id, "output": output})

    def _add(self, kind: str, data: dict[str, Any]) -> None:
        record = EpisodicRecord(kind=kind, data=data)
        self._records.append(record)
        if self.path:
            try:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(asdict(record), default=str) + "\n")
            except OSError:
                pass  # persistence is best-effort; never break the run

    # --- readers -------------------------------------------------------
    def all(self) -> list[EpisodicRecord]:
        return list(self._records)

    def recent(self, n: int = 5) -> list[EpisodicRecord]:
        return self._records[-n:]

    def render_recent(self, n: int = 5) -> str:
        lines: list[str] = []
        for r in self.recent(n):
            if r.kind == "event":
                lines.append(f"- [event] {r.data.get('type')} from {r.data.get('source')}")
            elif r.kind == "action":
                lines.append(f"- [action] called {r.data.get('tool')}({r.data.get('input')})")
            elif r.kind == "response":
                out = str(r.data.get("output", ""))
                lines.append(f"- [response] {out[:140]}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._records)


def _safe(value: Any) -> Any:
    """Best-effort JSON-friendly coercion for logging."""
    try:
        json.dumps(value, default=str)
        return value
    except (TypeError, ValueError):
        return str(value)

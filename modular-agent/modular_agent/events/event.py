"""Module 3 — the world-event data shape.

A ``WorldEvent`` is the unit the outside world (the Event Generator, another
program, a test) hands to the agent. It is intentionally generic so any
producer can describe "something happened" without knowing the agent internals.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorldEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    type: str  # e.g. "news_article", "ceo_statement", "viral_post"
    source: str = "unknown"  # who produced it
    payload: dict = Field(default_factory=dict)  # arbitrary event body
    timestamp: datetime = Field(default_factory=_now)

    def render(self) -> str:
        """Render the event as the human turn the LLM reads."""
        body = json.dumps(self.payload, indent=2, default=str)
        return (
            f"A new event has occurred in the world.\n"
            f"- type: {self.type}\n"
            f"- source: {self.source}\n"
            f"- time: {self.timestamp.isoformat()}\n"
            f"- details:\n{body}\n\n"
            f"React to this event in character, using your available tools where appropriate."
        )

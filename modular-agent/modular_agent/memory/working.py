"""Module 4b — working memory.

The short-term conversation buffer for the agent, carried across invokes so the
persona has continuity. Bounded to the most recent ``max_messages`` entries.
LangChain message classes are imported lazily so this module stays importable
without the LangChain stack (handy for unit tests).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage


class WorkingMemory:
    def __init__(self, max_messages: int = 20) -> None:
        self.max_messages = max_messages
        self._messages: list[Any] = []

    def add_user(self, text: str) -> None:
        from langchain_core.messages import HumanMessage

        self._append(HumanMessage(content=text))

    def add_ai(self, text: str) -> None:
        from langchain_core.messages import AIMessage

        self._append(AIMessage(content=text))

    def _append(self, message: "BaseMessage") -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages :]

    def messages(self) -> list["BaseMessage"]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)

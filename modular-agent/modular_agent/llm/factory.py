"""Module 1 — LLM provider selection.

``build_llm`` returns a LangChain chat model for whichever provider the config
names. Both returned models expose the same ``.bind_tools`` / ``.ainvoke``
interface, so the reasoning loop never has to care which one it got.

Provider SDK packages are imported lazily so that installing only the provider
you use is enough (e.g. an agent on Claude never needs ``langchain-google-genai``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import AgentConfig

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


def build_llm(config: AgentConfig) -> "BaseChatModel":
    """Instantiate the chat model described by ``config``."""
    if config.provider == "claude":
        from langchain_anthropic import ChatAnthropic

        kwargs: dict = {"model": config.model, "max_tokens": config.max_tokens}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        # NOTE: temperature/top_p are rejected by Opus 4.8 / Sonnet 5, so they
        # are deliberately never forwarded for the Claude provider.
        return ChatAnthropic(**kwargs)

    if config.provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        kwargs = {"model": config.model, "max_output_tokens": config.max_tokens}
        if config.api_key:
            kwargs["google_api_key"] = config.api_key
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature
        return ChatGoogleGenerativeAI(**kwargs)

    raise ValueError(f"Unknown LLM provider: {config.provider!r}")

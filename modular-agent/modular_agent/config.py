"""Agent configuration (Module 1 + 2 + 5 knobs).

A developer shapes an agent almost entirely through :class:`AgentConfig`:
which LLM provider/model to use, which MCP servers + tools it may touch,
and its hard token budget. Everything here is plain data (pydantic), so a
config can be built in code, loaded from env, or serialized to disk.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

Provider = Literal["claude", "gemini"]


class MCPServerConfig(BaseModel):
    """One MCP server the agent is allowed to reach.

    ``allowed_tools`` is the allowlist (Module 2): either the literal ``"*"``
    (all tools the server exposes) or an explicit list of tool names. Anything
    the server exposes that is not on the list is dropped before the LLM ever
    sees it.
    """

    url: str
    transport: Literal["streamable_http"] = "streamable_http"
    # /mcp/social binds identity per session, so a `login` tool call is made
    # once right after connecting, before any other tool is used.
    requires_login: bool = False
    login_name: str | None = None
    allowed_tools: list[str] | Literal["*"] = "*"

    def allows(self, tool_name: str) -> bool:
        return self.allowed_tools == "*" or tool_name in self.allowed_tools


class AgentConfig(BaseModel):
    """Top-level agent configuration."""

    # --- Module 1: LLM ---
    provider: Provider = "claude"
    model: str = "claude-haiku-4-5"  # fast/cheap default; swap freely
    api_key: str | None = None  # falls back to provider env var if None
    max_tokens: int = 4096  # per-response cap handed to the model
    # Only forwarded to providers that accept it (Gemini). Opus 4.8/Sonnet 5
    # reject `temperature`, so it is never sent for the Claude provider.
    temperature: float | None = None

    # --- Module 2: MCP tool allowlist ---
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)

    # --- Module 5: hard token limit + monitoring ---
    token_budget: int = 100_000  # cumulative hard cap across the whole run
    warn_threshold: float = 0.8  # fraction of budget that flips the warn state

    # Safety valve so a runaway tool-calling loop can't spin forever.
    max_iterations: int = 8

    @classmethod
    def from_env(cls, **overrides) -> "AgentConfig":
        """Build a config from environment variables (+ explicit overrides).

        Reads ``LLM_PROVIDER``, ``LLM_MODEL``, ``ANTHROPIC_API_KEY`` /
        ``GOOGLE_API_KEY``, ``AGENT_TOKEN_BUDGET``, ``AGENT_MAX_TOKENS``.
        Explicit ``overrides`` win over env values. Call sites that need MCP
        servers set them via ``overrides`` (they don't map cleanly to env).
        """
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:  # dotenv is optional at runtime
            pass

        provider: Provider = overrides.pop("provider", os.getenv("LLM_PROVIDER", "claude"))  # type: ignore[assignment]
        default_model = "claude-haiku-4-5" if provider == "claude" else "gemini-2.5-pro"
        model = overrides.pop("model", os.getenv("LLM_MODEL", default_model))

        api_key = overrides.pop("api_key", None)
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY") if provider == "claude" else os.getenv("GOOGLE_API_KEY")

        data = {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "token_budget": int(os.getenv("AGENT_TOKEN_BUDGET", "100000")),
            "max_tokens": int(os.getenv("AGENT_MAX_TOKENS", "4096")),
        }
        data.update(overrides)
        return cls(**data)

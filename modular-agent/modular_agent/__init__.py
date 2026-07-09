"""modular-agent: a configurable LangChain agent baseline.

Light imports only at package load (pydantic-backed config / events / persona).
The heavier pieces that pull in LangChain (`ModularAgent`, the MCP tool
provider, the monitor) are exposed lazily via ``__getattr__`` so that importing
a leaf module (e.g. for a unit test) doesn't drag in the whole stack.
"""

from __future__ import annotations

from .config import AgentConfig, MCPServerConfig
from .events import EventInbox, WorldEvent

__all__ = [
    "AgentConfig",
    "MCPServerConfig",
    "WorldEvent",
    "EventInbox",
    "ModularAgent",
    "RunResult",
    "TokenBudgetExceeded",
    "MCPToolProvider",
]


def __getattr__(name: str):  # PEP 562 lazy attribute access
    if name in ("ModularAgent", "RunResult"):
        from .loop.agent import ModularAgent, RunResult

        return {"ModularAgent": ModularAgent, "RunResult": RunResult}[name]
    if name == "TokenBudgetExceeded":
        from .monitor.callback import TokenBudgetExceeded

        return TokenBudgetExceeded
    if name == "MCPToolProvider":
        from .tools.mcp_client import MCPToolProvider

        return MCPToolProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Module 2 — MCP tool provider + allowlist filtering.

Connects to one or more MCP servers over Streamable-HTTP, performs the one-time
``login`` handshake where required (``/mcp/social`` binds identity per session),
loads each server's tools as LangChain tools, and filters them down to the
developer's allowlist before handing them to the agent.

The ``mcp`` / ``langchain-mcp-adapters`` imports are done lazily inside
:meth:`connect` so that ``filter_tools`` (and this module) can be imported in a
unit test without the MCP stack installed.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from ..config import MCPServerConfig

log = logging.getLogger(__name__)


def filter_tools(tools: list[Any], allowed: list[str] | str) -> list[Any]:
    """Return only the tools whose ``.name`` is on the allowlist.

    ``allowed`` is either the literal ``"*"`` (keep everything) or a list of
    tool names. Names in the allowlist that the server didn't expose are logged
    as a warning so typos surface early.
    """
    if allowed == "*":
        return list(tools)

    allow_set = set(allowed)
    by_name = {getattr(t, "name", None): t for t in tools}
    missing = allow_set - set(by_name)
    if missing:
        log.warning("allowlisted tools not exposed by server: %s", sorted(missing))
    return [t for name, t in by_name.items() if name in allow_set]


class MCPToolProvider:
    """Opens persistent MCP sessions and yields the combined, filtered tools."""

    def __init__(self, servers: dict[str, MCPServerConfig]) -> None:
        self.servers = servers

    @asynccontextmanager
    async def connect(self):
        """Async context manager yielding the list of allowlisted LangChain tools.

        Sessions stay open for the lifetime of the ``async with`` block — this
        matters for ``/mcp/social``, whose identity is bound to the session by
        the ``login`` call, so every subsequent tool acts as that user.
        """
        from contextlib import AsyncExitStack

        from langchain_mcp_adapters.tools import load_mcp_tools
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with AsyncExitStack() as stack:
            all_tools: list[Any] = []
            for name, cfg in self.servers.items():
                read, write, _ = await stack.enter_async_context(streamablehttp_client(cfg.url))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()

                if cfg.requires_login:
                    await session.call_tool("login", {"name": cfg.login_name or "agent"})

                server_tools = await load_mcp_tools(session)
                kept = filter_tools(server_tools, cfg.allowed_tools)
                log.info("MCP server %r: %d tools exposed, %d allowed", name, len(server_tools), len(kept))
                all_tools.extend(kept)

            yield all_tools

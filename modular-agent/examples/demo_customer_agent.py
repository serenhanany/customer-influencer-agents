"""Demo: a loyal-customer persona reacting to a contamination rumor.

Configures the modular-agent baseline into a single customer persona, connects
to the Social Network MCP servers with a small tool allowlist, injects one world
event, and runs the loop under the live monitor dashboard.

Run (requires the social network up, and — for a real model call — a key you've
been given explicit permission to use):

    docker compose up social-network        # from the repo root
    python examples/demo_customer_agent.py   # from modular-agent/

Point MCP_SOCIAL_URL / MCP_ANALYTICS_URL at http://localhost:3005/... on the host.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Make `modular_agent` importable when this script is run directly from
# examples/ (that folder, not the project root, is what lands on sys.path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modular_agent import AgentConfig, MCPServerConfig, ModularAgent, WorldEvent
from modular_agent.persona import Identity, Objectives, Persona, Voice
from modular_agent.tools import MCPToolProvider

SOCIAL_URL = os.getenv("MCP_SOCIAL_URL", "http://localhost:3005/mcp/social")
ANALYTICS_URL = os.getenv("MCP_ANALYTICS_URL", "http://localhost:3005/mcp/analytics")


def build_agent() -> ModularAgent:
    config = AgentConfig.from_env(
        token_budget=50_000,
        mcp_servers={
            "social": MCPServerConfig(
                url=SOCIAL_URL,
                requires_login=True,
                login_name="Dana (loyal customer)",
                allowed_tools=["login", "get_global_feed", "search", "create_post", "add_comment"],
            ),
            "analytics": MCPServerConfig(
                url=ANALYTICS_URL,
                allowed_tools=["get_overview", "get_trends"],
            ),
        },
    )

    persona = Persona(
        identity=Identity(
            name="Dana",
            role="a loyal HappyTuna customer of 10 years",
            backstory="You buy HappyTuna every week for your family and have always trusted the brand.",
        ),
        voice=Voice(tone="warm but increasingly worried", verbosity="concise"),
        objectives=Objectives(
            items=[
                "Protect your family's safety above all.",
                "Stay loyal to HappyTuna unless your trust is genuinely broken.",
                "Voice your concerns publicly and honestly.",
            ]
        ),
    )
    return ModularAgent(config, persona)


async def main() -> None:
    agent = build_agent()
    event = WorldEvent(
        type="news_article",
        source="brightwatch-news",
        payload={
            "headline": "Rumors swirl about possible contamination in HappyTuna cans",
            "summary": "An unverified social post claims a shopper found spoiled product. No official confirmation yet.",
        },
    )

    async with MCPToolProvider(agent.config.mcp_servers).connect() as tools:
        with agent.monitor.live():
            result = await agent.run(event, tools=tools)

    print("\n--- agent output ---")
    print(result.output or f"(aborted: {result.error})")
    print("\n--- monitor summary ---")
    print(agent.monitor.summary())


if __name__ == "__main__":
    asyncio.run(main())

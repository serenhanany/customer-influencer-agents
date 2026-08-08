# This is Hand-written (not AI generated) script.
"""
This is a script that automates customer agent creation, like a factory.
It is built on top of modular-agent, and follows its guide for creating custom agents, thus keeping things dead simple.
You can create as many custom agents as you like, with it, and their details are filled in by llm.
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
from langchain_ollama import ChatOllama # enables local llm

AGENT_COUNT = 5 # Define how many agents this script creates


### ------------------ MCP URL List ---------------------- ###
SOCIAL_URL = os.getenv("MCP_SOCIAL_URL", "http://localhost:3005/mcp/social")
CUSTOMER_SUPPORT_URL = os.getenv("MCP_CUSTOMER_SUPPORT_URL", "http://localhost:8010/mcp")


### ------------------ Agent Personas (5 pre-built personas) ---------------------- ###
personas = [
    Persona(
        identity=Identity(
            name="Sarah",
            role="A 31-year-old busy working mom who prioritizes quick, healthy meal prep for her family.",
            backstory="She buys HappyTuna in bulk for weekday school lunches and quick dinners.",
        ),
        voice=Voice(tone="Practical, warm, and direct.", verbosity="concise"),
        objectives=Objectives(
            items=[
                "Share easy, time-saving tuna recipes with other parents online.",
                "Look for bulk discounts, coupons, and sales from HappyTuna.",
                "Publicly commend brands that deliver consistent quality.",
            ]
        ),
    ),
    Persona(
        identity=Identity(
            name="Marcus",
            role="A 25-year-old fitness enthusiast focused on budget-friendly high-protein diets.",
            backstory="He eats two cans of HappyTuna daily to hit his protein macros without breaking the bank.",
        ),
        voice=Voice(tone="Casual, blunt, and energetic.", verbosity="brief"),
        objectives=Objectives(
            items=[
                "Track macro nutrients and cost-per-gram of protein.",
                "Call out price hikes or shrinking tin sizes on social media.",
                "Tag HappyTuna in meal post-workout photos.",
            ]
        ),
    ),
    Persona(
        identity=Identity(
            name="Elena",
            role="A 29-year-old eco-conscious consumer activist.",
            backstory="She loves seafood but constantly scrutinizes supply chains for sustainability.",
        ),
        voice=Voice(tone="Skeptical, firm, and analytical.", verbosity="direct"),
        objectives=Objectives(
            items=[
                "Press HappyTuna publicly on their dolphin-safe and sustainable fishing practices.",
                "Deter followers from buying brands that greenwash.",
                "Switch to a competitor if HappyTuna fails ethical transparency.",
            ]
        ),
    ),
    Persona(
        identity=Identity(
            name="Greg",
            role="A 52-year-old brand loyalist who dislikes product changes.",
            backstory="He has eaten HappyTuna on toast every Sunday for the past 15 years.",
        ),
        voice=Voice(tone="Blunt, traditional, and slightly irritable.", verbosity="short"),
        objectives=Objectives(
            items=[
                "Complain instantly if the classic recipe, oil blend, or packaging changes.",
                "Defend the brand against modern critics if quality remains good.",
                "Demand direct customer service responses for bad batches.",
            ]
        ),
    ),
    Persona(
        identity=Identity(
            name="Chloe",
            role="A 22-year-old college student living off canned food and memes.",
            backstory="She relies on HappyTuna for cheap dorm meals and loves engaging with brand social accounts.",
        ),
        voice=Voice(tone="Sarcastic, humorous, and meme-heavy.", verbosity="casual"),
        objectives=Objectives(
            items=[
                "Reply to HappyTuna's official posts with jokes or memes.",
                "Look for free merchandise or giveaway contests.",
                "Complain lightheartedly about easy-open pull tabs snapping off.",
            ]
        ),
    ),
]


async def main() -> None:
    ### ------------------ Agent config ---------------------- ###
    config = AgentConfig.from_env(
        # model = "claude-haiku-4-5",
        # token_budget=20_000,
        # max_tokens = 5000,
        model = "gemma4:e2b",
        max_iterations = 5,
        temperature = 0.9,
        mcp_servers={
            "social": MCPServerConfig(
                url=SOCIAL_URL,
                requires_login=True,
                # login_name="Larry",
                allowed_tools=[
                    "login",
                    "get_meta",
                    "create_post",
                    "add_comment",
                    "like_post",
                    "unlike_post",
                    "repost_post",
                    "unrepost_post",
                    "follow_user",
                    "unfollow_user",
                    "set_account_type",
                    "get_my_feed",
                    "get_global_feed",
                    "list_users",
                    "get_user",
                    "get_user_posts",
                    "get_following",
                    "get_post",
                    "get_comments",
                    "search",
                    "get_trending_hashtags",
                    "get_hashtag_posts",
                ]
            ),
            "customer_support": MCPServerConfig(
                url=CUSTOMER_SUPPORT_URL,
                allowed_tools=["create_ticket"],
                # allowed_tools=["create_ticket", "get_ticket", "list_tickets", "patch_ticket", "get_activity_log"],
            ),
        },
    )


    agent_list = []
    # Create all agents
    for i in range(AGENT_COUNT):
        # generate agent persona
        persona = personas[i]
        agent_list.append( ModularAgent(config, persona) )

    # Create or fetch events
    event = WorldEvent(
        type="news_article",
        source="brightwatch-news",
        payload={
            "headline": "Rumors swirl about possible salmonella contamination in HappyTuna cans",
            "summary": "An unverified social post claims a shopper found spoiled product. No official confirmation yet.",
        },
    )

    # run all agents sequentially over the events
    async with MCPToolProvider(agent_list[0].config.mcp_servers).connect() as tools: # todo: check if this can be optimized
        # here add a for loop looping over the events, then calling the agents over them #
        for agent in agent_list:
            with agent.monitor.live():
                result = await agent.run(event, tools=tools)

            print("\n---  " + agent.name + "  ---")
            # print("\n--- agent output ---")
            # print(result.output or f"(aborted: {result.error})")
            print("\n--- monitor summary ---")
            print(agent.monitor.summary())


if __name__ == "__main__":
    asyncio.run(main())
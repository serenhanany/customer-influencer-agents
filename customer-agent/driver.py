"""
Autonomous driver: subscribes to the event generator and reacts to crisis
events on behalf of every persona, without waiting to be called.

Drives the workflow the same way test_workflow.py does -- in-process, via
nat.runtime.loader.load_workflow -- rather than by making an MCP call to
our own "nat mcp serve" process. That would be a pointless network hop to
ourselves; load_workflow gives a direct async handle to the same decision
function nat mcp serve exposes.

Runs as its own asyncio task inside main.py, alongside "nat mcp serve" as a
subprocess. The two paths end up with separate in-memory persona state
(register.py's _memory is a plain module-level dict, and "nat mcp serve"
lives in a different OS process) -- this doubles that existing limitation
rather than introducing a new one; see register.py's note at the bottom.
"""
from __future__ import annotations

import asyncio
import logging
import os

from event_client import subscribe
from personas import all_persona_ids

import register  # noqa: F401  -- registers customer_agent_decision
import nat.plugins.mcp.register  # noqa: F401  -- registers mcp_client
from nat.runtime.loader import load_workflow

logger = logging.getLogger(__name__)

# Which event-generator tags customers should react to. Per the crisis feed
# in event-generator/event_generator.py: "social" is viral/social chatter,
# "press" is published news coverage -- both are things a customer persona
# would plausibly see and react to. "regulator" (FDA/legal notices) is not
# customer-facing, so it's deliberately excluded by default.
DEFAULT_EVENT_TAGS = ("social", "press")


def _event_tags() -> tuple[str, ...]:
    raw = os.environ.get("CUSTOMER_AGENT_EVENT_TAGS")
    if not raw:
        return DEFAULT_EVENT_TAGS
    return tuple(tag.strip() for tag in raw.split(",") if tag.strip())


async def _react(workflow, persona_id: str, event_text: str) -> None:
    try:
        async with workflow.run({"persona_id": persona_id, "event": event_text}) as runner:
            result = await runner.result(to_type=dict)
    except Exception:
        logger.exception("customer_agent_decision failed for persona=%s", persona_id)
        return

    decision = result.get("decision") or {}
    ticket = result.get("ticket")
    logger.info(
        "persona=%s action=%s ticket=%s",
        persona_id,
        decision.get("action"),
        ticket["ticket_id"] if ticket else None,
    )


async def run() -> None:
    tags = _event_tags()
    persona_ids = all_persona_ids()
    logger.info("Listening for tags %s, reacting as personas %s", tags, persona_ids)

    async with load_workflow("workflow.yml") as workflow:
        async for event in subscribe(*tags):
            logger.info("event tag=%s seq=%s: %s", event.tag, event.seq, event.text[:80])
            # Sequential, not gathered: keeps this friendly to the NIM API's
            # rate limits and avoids concurrent writers to the same _memory
            # dict entry -- a burst of 5 simultaneous LLM calls per event
            # isn't needed for a scripted 5-event demo feed.
            for persona_id in persona_ids:
                await _react(workflow, persona_id, event.text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run())

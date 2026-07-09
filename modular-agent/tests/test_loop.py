"""Module 4c — the loop runs its stages in order and records to memory.

Uses a subclassed agent whose ``reason_act`` is stubbed, so the test needs no
LLM, API key, or network.
"""

import asyncio

from modular_agent import AgentConfig, WorldEvent
from modular_agent.loop.agent import ModularAgent
from modular_agent.persona import Identity, Persona


class _FakeAction:
    def __init__(self, tool, tool_input):
        self.tool = tool
        self.tool_input = tool_input


class StubAgent(ModularAgent):
    async def reason_act(self, human_input, context, tools):
        # Pretend the agent called one tool, then produced a response.
        steps = [(_FakeAction("create_post", {"content": "I'm worried!"}), "post_id=42")]
        return "I posted my concern.", steps


def _agent():
    config = AgentConfig(token_budget=10_000)
    persona = Persona(identity=Identity(name="Dana", role="loyal customer"))
    return StubAgent(config, persona)


def test_run_stage_order_and_recording():
    agent = _agent()
    event = WorldEvent(type="news_article", payload={"headline": "rumor"})

    result = asyncio.run(agent.run(event))

    assert not result.aborted
    assert result.output == "I posted my concern."

    # Stage order captured on the timeline.
    timeline = agent.monitor.metrics.invokes[-1].timeline
    assert timeline == ["perceive", "recall", "reflect", "respond"]

    # Episodic memory recorded the event, the action, and the response.
    kinds = [r.kind for r in agent.memory.episodic.all()]
    assert kinds == ["event", "action", "response"]

    # Working memory now carries the exchange.
    assert len(agent.memory.working) == 2


def test_budget_abort_is_clean():
    config = AgentConfig(token_budget=100)

    class OverBudgetAgent(ModularAgent):
        async def reason_act(self, human_input, context, tools):
            from modular_agent.monitor.callback import TokenBudgetExceeded

            raise TokenBudgetExceeded("simulated overrun")

    agent = OverBudgetAgent(config, Persona(identity=Identity(name="X", role="y")))
    result = asyncio.run(agent.run(WorldEvent(type="x")))

    assert result.aborted
    assert "overrun" in result.error
    assert result.output == ""

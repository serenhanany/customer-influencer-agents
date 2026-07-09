"""Module 4c — the reasoning loop.

``ModularAgent`` ties the modules together and runs one explicit cycle per
event: Perceive → Recall → Reason → Act → Reflect → Respond. Each stage is a
method a specialized agent can override. The Reason↔Act inner loop uses
LangChain's tool-calling agent; the surrounding stages are our own so they stay
testable without the LLM stack.

LangChain imports are done lazily inside :meth:`reason_act` so the rest of the
class (and unit tests that stub ``reason_act``) don't require the full stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config import AgentConfig
from ..events.event import WorldEvent
from ..memory.bundle import MemoryBundle
from ..monitor.callback import TokenBudgetExceeded
from ..monitor.monitor import Monitor
from ..persona.persona import Persona


@dataclass
class _Action:
    """Lightweight stand-in for a tool invocation, for episodic logging."""

    tool: str
    tool_input: Any


def _text(content: Any) -> str:
    """Coerce a message ``content`` (str or list-of-blocks) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", "") or "")
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _extract_steps(messages: list[Any]) -> list[tuple["_Action", str]]:
    """Reconstruct (action, observation) pairs from the message trace."""
    observations: dict[Any, str] = {}
    for m in messages:
        if getattr(m, "type", None) == "tool" or m.__class__.__name__ == "ToolMessage":
            observations[getattr(m, "tool_call_id", None)] = _text(getattr(m, "content", ""))

    steps: list[tuple[_Action, str]] = []
    for m in messages:
        for tc in getattr(m, "tool_calls", None) or []:
            get = tc.get if isinstance(tc, dict) else (lambda k, _tc=tc: getattr(_tc, k, None))
            steps.append((_Action(get("name"), get("args")), observations.get(get("id"), "")))
    return steps


@dataclass
class RunResult:
    output: str
    invoke_id: str
    aborted: bool = False
    error: str | None = None
    tool_calls: int = 0
    steps: list[Any] = field(default_factory=list)


class ModularAgent:
    def __init__(
        self,
        config: AgentConfig,
        persona: Persona,
        memory: MemoryBundle | None = None,
        monitor: Monitor | None = None,
        name: str | None = None,
    ) -> None:
        self.config = config
        self.persona = persona
        self.memory = memory or MemoryBundle()
        self.monitor = monitor or Monitor(config)
        self.name = name or persona.identity.name
        self._llm = None  # lazily built

    # --- public entrypoint --------------------------------------------
    async def run(self, event: WorldEvent, tools: list[Any] | None = None) -> RunResult:
        tools = tools or []
        invoke = self.monitor.metrics.start_invoke(self.config.model)
        try:
            human_input = self.perceive(event)
            context = self.recall(event)
            output, steps = await self.reason_act(human_input, context, tools)
            self.reflect(event, output, steps)
            invoke.timeline.append("respond")
            return RunResult(output=output, invoke_id=invoke.invoke_id,
                             tool_calls=len(steps), steps=steps)
        except TokenBudgetExceeded as exc:
            return RunResult(output="", invoke_id=invoke.invoke_id, aborted=True, error=str(exc))
        finally:
            self.monitor.metrics.end_invoke()

    # --- stages (overridable) -----------------------------------------
    def perceive(self, event: WorldEvent) -> str:
        """Normalize the event and log it to episodic memory."""
        self.memory.episodic.record_event(event)
        if self.monitor.metrics.current is not None:
            self.monitor.metrics.current.timeline.append("perceive")
        return event.render()

    def recall(self, event: WorldEvent) -> str:
        """Pull relevant memory into a context string for this invoke."""
        if self.monitor.metrics.current is not None:
            self.monitor.metrics.current.timeline.append("recall")
        return self.memory.retrieval.build_context(event, self.memory)

    async def reason_act(self, human_input: str, context: str, tools: list[Any]):
        """LLM reasoning + tool calls. Returns (output_text, steps).

        Uses LangChain 1.x's ``create_agent`` — a tool-calling loop that runs
        until the model stops requesting tools. With an empty ``tools`` list it
        degrades to a single model call. The monitor callback rides along via
        the run config, so token/tool events are captured either way.
        """
        from langchain.agents import create_agent
        from langchain_core.messages import HumanMessage

        system = self.persona.system_prompt()
        if context:
            system += "\n\n# Relevant memory\n" + context

        agent = create_agent(self._model(), tools or [], system_prompt=system)

        messages = list(self.memory.working.messages()) + [HumanMessage(content=human_input)]
        run_config = {
            "callbacks": [self.monitor.callback],
            "recursion_limit": self.config.max_iterations * 2 + 1,
        }
        result = await agent.ainvoke({"messages": messages}, config=run_config)

        out_messages = result.get("messages", [])
        output = _text(out_messages[-1].content) if out_messages else ""
        return output, _extract_steps(out_messages)

    def reflect(self, event: WorldEvent, output: str, steps: list[Any]) -> None:
        """Write the outcome back to memory (episodic log + working buffer)."""
        for step in steps:
            try:
                action, observation = step
                self.memory.episodic.record_action(
                    getattr(action, "tool", "tool"),
                    getattr(action, "tool_input", None),
                    observation,
                )
            except (ValueError, TypeError):
                continue
        self.memory.episodic.record_response(event.id, output)
        self.memory.working.add_user(event.render())
        self.memory.working.add_ai(output)
        if self.monitor.metrics.current is not None:
            self.monitor.metrics.current.timeline.append("reflect")

    # --- helpers -------------------------------------------------------
    def _model(self):
        if self._llm is None:
            from ..llm.factory import build_llm

            self._llm = build_llm(self.config)
        return self._llm

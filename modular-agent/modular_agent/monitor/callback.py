"""Module 5 — LangChain callback: token tracking + hard-cap enforcement.

``MonitorCallback`` observes the LLM/tool events LangChain emits and folds them
into the shared :class:`RunMetrics`. The hard token cap is enforced *before* a
call: if the cumulative budget is already spent when a new LLM call is about to
start, it raises :class:`TokenBudgetExceeded`, which aborts the run cleanly
rather than letting it overrun.
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from .metrics import RunMetrics, ToolCall
from .pricing import estimate_cost


class TokenBudgetExceeded(RuntimeError):
    """Raised when the cumulative token budget would be exceeded by a new call."""


class MonitorCallback(BaseCallbackHandler):
    def __init__(self, metrics: RunMetrics, model: str) -> None:
        self.metrics = metrics
        self.model = model
        self._tool_starts: dict[Any, float] = {}

    # --- LLM lifecycle -------------------------------------------------
    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
        self._guard_budget()

    def on_llm_start(self, serialized, prompts, **kwargs) -> None:
        # Some providers emit on_llm_start instead of on_chat_model_start.
        self._guard_budget()

    def on_llm_end(self, response, **kwargs) -> None:
        inp, out = _extract_usage(response)
        cur = self.metrics.current
        if cur is None:
            return
        cur.input_tokens += inp
        cur.output_tokens += out
        cur.cost_usd += estimate_cost(self.model, inp, out)

    def on_llm_error(self, error, **kwargs) -> None:
        if self.metrics.current is not None:
            self.metrics.current.errors.append(f"llm: {error}")

    # --- tool lifecycle ------------------------------------------------
    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        run_id = kwargs.get("run_id")
        self._tool_starts[run_id] = time.monotonic()
        name = (serialized or {}).get("name", "tool")
        if self.metrics.current is not None:
            self.metrics.current.timeline.append(f"act:{name}")

    def on_tool_end(self, output, **kwargs) -> None:
        self._finish_tool(kwargs.get("run_id"), kwargs.get("name"), ok=True)

    def on_tool_error(self, error, **kwargs) -> None:
        self._finish_tool(kwargs.get("run_id"), kwargs.get("name"), ok=False)
        if self.metrics.current is not None:
            self.metrics.current.errors.append(f"tool: {error}")

    # --- helpers -------------------------------------------------------
    def _guard_budget(self) -> None:
        cur = self.metrics.current
        if cur is not None:
            cur.llm_calls += 1
            cur.timeline.append("reason")
        if self.metrics.over_budget:
            raise TokenBudgetExceeded(
                f"token budget of {self.metrics.budget} reached "
                f"(used {self.metrics.cumulative_tokens}); aborting before next call"
            )

    def _finish_tool(self, run_id: Any, name: str | None, ok: bool) -> None:
        started = self._tool_starts.pop(run_id, None)
        latency = (time.monotonic() - started) if started else 0.0
        if self.metrics.current is not None:
            self.metrics.current.tool_calls.append(
                ToolCall(name=name or "tool", ok=ok, latency_s=latency)
            )


def _extract_usage(response) -> tuple[int, int]:
    """Pull (input_tokens, output_tokens) from an LLMResult, best-effort."""
    # Preferred: usage_metadata on the generation's message (chat models).
    for gen_list in getattr(response, "generations", []) or []:
        for gen in gen_list:
            msg = getattr(gen, "message", None)
            um = getattr(msg, "usage_metadata", None) if msg is not None else None
            if um:
                return int(um.get("input_tokens", 0)), int(um.get("output_tokens", 0))

    # Fallback: llm_output usage/token_usage dict.
    llm_output = getattr(response, "llm_output", None) or {}
    usage = llm_output.get("usage") or llm_output.get("token_usage") or {}
    inp = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
    out = usage.get("output_tokens") or usage.get("completion_tokens") or 0
    return int(inp), int(out)

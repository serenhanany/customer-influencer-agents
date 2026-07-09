"""Module 5 — structured metrics.

``RunMetrics`` is the single source of truth the dashboard renders. It holds one
``InvokeMetrics`` per ``agent.run(...)`` plus run-wide cumulative views and the
token budget state. Everything here is plain dataclasses, so it can be logged,
serialized, or fed to a different renderer (e.g. a web UI) later.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    name: str
    ok: bool = True
    latency_s: float = 0.0


@dataclass
class InvokeMetrics:
    invoke_id: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    llm_calls: int = 0
    tool_calls: list[ToolCall] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    started: float = field(default_factory=time.monotonic)
    latency_s: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class RunMetrics:
    budget: int
    warn_threshold: float = 0.8
    invokes: list[InvokeMetrics] = field(default_factory=list)
    current: InvokeMetrics | None = None

    # --- lifecycle -----------------------------------------------------
    def start_invoke(self, model: str) -> InvokeMetrics:
        im = InvokeMetrics(invoke_id=f"inv-{len(self.invokes) + 1}", model=model)
        self.invokes.append(im)
        self.current = im
        return im

    def end_invoke(self) -> None:
        if self.current is not None:
            self.current.latency_s = time.monotonic() - self.current.started
            self.current = None

    # --- cumulative views ---------------------------------------------
    @property
    def cumulative_input_tokens(self) -> int:
        return sum(i.input_tokens for i in self.invokes)

    @property
    def cumulative_output_tokens(self) -> int:
        return sum(i.output_tokens for i in self.invokes)

    @property
    def cumulative_tokens(self) -> int:
        return self.cumulative_input_tokens + self.cumulative_output_tokens

    @property
    def cumulative_cost(self) -> float:
        return sum(i.cost_usd for i in self.invokes)

    @property
    def remaining_tokens(self) -> int:
        return self.budget - self.cumulative_tokens

    @property
    def over_budget(self) -> bool:
        return self.cumulative_tokens >= self.budget

    @property
    def warned(self) -> bool:
        return self.cumulative_tokens >= self.budget * self.warn_threshold

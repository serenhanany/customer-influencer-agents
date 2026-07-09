"""Module 5 — Monitor: ties metrics + callback + dashboard together."""

from __future__ import annotations

from ..config import AgentConfig
from .callback import MonitorCallback
from .dashboard import Dashboard
from .metrics import RunMetrics


class Monitor:
    def __init__(self, config: AgentConfig) -> None:
        self.metrics = RunMetrics(budget=config.token_budget, warn_threshold=config.warn_threshold)
        self.callback = MonitorCallback(self.metrics, model=config.model)

    def live(self) -> Dashboard:
        """Return a context manager that renders the live terminal dashboard."""
        return Dashboard(self.metrics)

    def summary(self) -> str:
        """Plain-text one-liner (handy when no TTY / dashboard is used)."""
        m = self.metrics
        return (
            f"invokes={len(m.invokes)} tokens={m.cumulative_tokens:,}/{m.budget:,} "
            f"cost=${m.cumulative_cost:.4f} remaining={m.remaining_tokens:,}"
        )

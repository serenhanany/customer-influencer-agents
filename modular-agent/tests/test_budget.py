"""Module 5 — the hard token cap aborts BEFORE a call, not after."""

import pytest

from modular_agent.monitor.callback import MonitorCallback, TokenBudgetExceeded
from modular_agent.monitor.metrics import RunMetrics


def test_guard_raises_once_budget_spent():
    metrics = RunMetrics(budget=100)
    cb = MonitorCallback(metrics, model="claude-haiku-4-5")
    metrics.start_invoke("claude-haiku-4-5")
    metrics.current.input_tokens = 150  # already over the 100-token cap

    with pytest.raises(TokenBudgetExceeded):
        cb.on_chat_model_start({}, [])


def test_guard_allows_call_under_budget():
    metrics = RunMetrics(budget=100_000)
    cb = MonitorCallback(metrics, model="claude-haiku-4-5")
    metrics.start_invoke("claude-haiku-4-5")

    cb.on_chat_model_start({}, [])  # must not raise
    assert metrics.current.llm_calls == 1

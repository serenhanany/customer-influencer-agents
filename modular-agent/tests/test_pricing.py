"""Module 5 — pricing table + cost estimate."""

from modular_agent.monitor.pricing import estimate_cost, is_known


def test_haiku_is_default_and_priced():
    assert is_known("claude-haiku-4-5")
    # 1M in @ $1, 1M out @ $5 -> $6
    assert estimate_cost("claude-haiku-4-5", 1_000_000, 1_000_000) == 6.0


def test_partial_tokens():
    # 1000 in @ $1/M + 2000 out @ $5/M = 0.001 + 0.010 = 0.011
    assert round(estimate_cost("claude-haiku-4-5", 1000, 2000), 6) == 0.011


def test_unknown_model_is_zero():
    assert not is_known("made-up-model")
    assert estimate_cost("made-up-model", 10_000, 10_000) == 0.0

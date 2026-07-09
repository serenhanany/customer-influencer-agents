"""Module 5 — model pricing table + cost estimation.

Prices are USD per 1,000,000 tokens as (input, output). Claude figures are from
the Anthropic pricing reference; the Gemini rows are approximate placeholders a
developer should confirm/adjust for their account. Unknown models estimate as
$0 and are flagged by ``is_known``.
"""

from __future__ import annotations

# (input $/Mtok, output $/Mtok)
PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    # Approximate — adjust to your Gemini pricing.
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-2.5-flash": (0.30, 2.50),
}


def is_known(model: str) -> bool:
    return model in PRICING


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost estimate for a call. Unknown models return 0.0."""
    p_in, p_out = PRICING.get(model, (0.0, 0.0))
    return (input_tokens / 1_000_000) * p_in + (output_tokens / 1_000_000) * p_out

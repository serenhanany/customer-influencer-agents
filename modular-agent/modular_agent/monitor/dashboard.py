"""Module 5 — rich live terminal dashboard.

Renders a :class:`RunMetrics` snapshot as a terminal panel and, via the
``Dashboard`` context manager, keeps it refreshing on a background thread while
the agent runs. It reads metrics only — all state lives in ``RunMetrics`` — so
the same data could drive a different renderer later.
"""

from __future__ import annotations

import threading
from collections import Counter

from .metrics import RunMetrics
from .pricing import is_known


def _budget_bar(used: int, budget: int, width: int = 16) -> str:
    # ASCII-only so it renders on every console (incl. legacy Windows cp1252).
    if budget <= 0:
        return "n/a"
    frac = min(1.0, used / budget)
    filled = int(frac * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def render(metrics: RunMetrics):
    """Build a rich renderable for the current metrics state."""
    from rich.panel import Panel
    from rich.table import Table

    cur = metrics.current or (metrics.invokes[-1] if metrics.invokes else None)

    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", style="bold cyan")
    table.add_column()

    model = cur.model if cur else "?"
    invoke_id = cur.invoke_id if cur else "-"
    table.add_row("invoke", f"{invoke_id}   model {model}"
                  + ("" if is_known(model) else "  [dim](no pricing)[/dim]"))

    if cur:
        table.add_row("tokens", f"in {cur.input_tokens:,}  out {cur.output_tokens:,}  "
                                f"({cur.total_tokens:,} this invoke)")
    table.add_row("cost", f"cumulative ${metrics.cumulative_cost:.4f}")

    used = metrics.cumulative_tokens
    warn = " [yellow](warn)[/yellow]" if metrics.warned else ""
    table.add_row("budget", f"{_budget_bar(used, metrics.budget)}  "
                            f"{metrics.remaining_tokens:,} / {metrics.budget:,} left{warn}")

    if cur:
        table.add_row("steps", f"{cur.llm_calls} LLM calls | {len(cur.tool_calls)} tool calls")
        if cur.tool_calls:
            counts = Counter(t.name for t in cur.tool_calls)
            fails = sum(1 for t in cur.tool_calls if not t.ok)
            slowest = max((t.latency_s for t in cur.tool_calls), default=0.0)
            summary = "  ".join(f"{n} x{c}" for n, c in counts.items())
            table.add_row("tools", summary + (f"   [red]{fails} failed[/red]" if fails else " (all ok)"))
            table.add_row("latency", f"{cur.latency_s:.1f}s invoke | {slowest:.1f}s slowest tool")
        else:
            table.add_row("latency", f"{cur.latency_s:.1f}s invoke")
        table.add_row("errors", "[red]" + "; ".join(cur.errors) + "[/red]" if cur.errors else "none")
        if cur.timeline:
            table.add_row("trace", " -> ".join(cur.timeline))

    return Panel(table, title="modular-agent monitor", border_style="cyan")


class Dashboard:
    """Context manager that live-refreshes the dashboard on a background thread."""

    def __init__(self, metrics: RunMetrics, refresh_hz: float = 4.0) -> None:
        self.metrics = metrics
        self._interval = 1.0 / refresh_hz
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._live = None

    def __enter__(self) -> "Dashboard":
        from rich.live import Live

        self._live = Live(render(self.metrics), refresh_per_second=8, transient=False)
        self._live.__enter__()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            if self._live is not None:
                self._live.update(render(self.metrics))

    def __exit__(self, *exc) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._live is not None:
            self._live.update(render(self.metrics))
            self._live.__exit__(*exc)

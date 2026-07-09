# modular-agent — Project Guide

## What this is
`modular-agent` is a reusable **LangChain (Python) agent baseline** for the BitriX / HappyTuna crisis
simulation (see the repo-root `PROJECT_README.md`). Concrete simulation agents — customer, influencer,
and eventually the CEO — are built by *configuring* this baseline and shaping its persona/memory, not
by re-implementing agent plumbing each time.

It is broken into five independently shapeable modules:
1. **LLM provider** (`llm/`) — Claude or Gemini, chosen by config + API key.
2. **MCP tool allowlist** (`tools/`) — which MCP servers + tool names the agent may use.
3. **World-event injection** (`events/`) — how external programs push events in.
4. **Internal logic** (`persona/`, `memory/`, `loop/`) — persona + memory + the reasoning loop.
5. **Token limits + monitoring** (`monitor/`) — hard token cap + live terminal dashboard.

Read [PLAN.md](./PLAN.md) for the full design, [TASKS.md](./TASKS.md) for current progress, and
[docs/DEVELOPER_GUIDE.md](./docs/DEVELOPER_GUIDE.md) for the developer-facing usage guide.

## Scope discipline
- **Only touch files under `modular-agent/`.** Do not modify `social_network/`, `customer-agent/`,
  `docker-compose.yml`, or any other service unless the user explicitly asks.
- The other agents (`customer-agent`, `influencer-agent`) are intended *consumers* of this baseline,
  but wiring them up is out of scope until requested.

## LLM / model policy
- Default model is **`claude-haiku-4-5`** (fast, low-cost tier — most simulated persona agents don't
  need more). Swappable via config to `claude-sonnet-5`, `claude-opus-4-8`, or the Gemini provider.
- **When writing or changing any code that calls Claude/Anthropic, load the `claude-api` skill first**
  — do not rely on memory for model IDs, pricing, or SDK shapes.
- Use exact model ID strings (`claude-haiku-4-5`, `claude-sonnet-5`, `claude-opus-4-8`) — never append
  date suffixes.
- Do **not** send `temperature`/`top_p` on the Claude path (rejected by Opus 4.8 / Sonnet 5); only
  forward `temperature` to Gemini.

## Coding standards
- **Python 3.11**, type hints on public functions, `from __future__ import annotations` at the top.
- **pydantic** for config and data models (`AgentConfig`, `MCPServerConfig`, `WorldEvent`, persona).
- **Lazy provider imports**: import `langchain_anthropic` / `langchain_google_genai` / `chromadb`
  inside the functions that need them, so installing only what you use is enough.
- Prefer small, overridable methods for the loop stages (Perceive/Recall/Reason/Act/Reflect/Respond).
- Follow the repo convention: a flat, **unpinned** `requirements.txt`; no `pyproject.toml`.
- Keep the baseline small — do not add infrastructure (extra services, queues) unless the scope
  actually needs it. The Reason↔Act loop uses LangChain 1.x `langchain.agents.create_agent` (the
  supported v1 tool-calling agent, LangGraph-backed internally); the older
  `create_tool_calling_agent` / `AgentExecutor` were removed in LangChain 1.x. Do not reintroduce them.

## Token budget & monitoring
- `token_budget` is a **hard cap**: enforce it by aborting *before* a call once cumulative usage is
  spent (raise `TokenBudgetExceeded`), never after overrunning.
- The monitor exposes a structured `RunMetrics` object; the `rich` live dashboard is one renderer of
  it (so a web UI could consume the same data later).

## Testing & running
- Tests live in `tests/`, run with `pytest`. Mock the LLM and MCP tools — unit tests must not need
  network or API keys.
- The demo/agent loop is **async** (MCP tools are async) — entry points use `asyncio.run(...)`.

## When you finish a unit of work
- Update the status boxes in [TASKS.md](./TASKS.md).
- If a design decision changes, reflect it in [PLAN.md](./PLAN.md) and the developer guide.


## NEVER USE REAL API KEY WITHOUT EXPLICIT USER PERMISSION.
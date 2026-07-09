# Plan: `modular-agent` — a reusable LangChain agent baseline

## Context

The BitriX/HappyTuna crisis simulation needs concrete AI agents (customer, influencer, and
eventually the CEO). Today `customer-agent/` and `influencer-agent/` are stubs (`print(...)` then
exit) and each would otherwise re-implement the same plumbing: picking an LLM, connecting to the
Social Network MCP servers, receiving world events, holding a persona + memory, and staying within a
token budget.

This directory will hold a **standalone, importable baseline** that a developer configures to produce
a real agent, rather than rewriting agent internals each time. Five modules, each independently
shapeable: **LLM provider**, **MCP tool allowlist**, **world-event injection**, **internal logic
(persona + memory + reasoning loop)**, and **token limits + monitoring**.

**Scope:** everything lives under `modular-agent/`. The other services (`customer-agent`,
`docker-compose.yml`, `social_network`, etc.) are **not modified**. A runnable **demo agent** is
included as an example only.

## Key facts grounding the design

- **MCP servers** (see `social_network/docs/mcp-tools.md`): two Streamable-HTTP endpoints on the
  social-network Express app. `/mcp/social` (22 participation tools; requires calling the **`login`**
  tool once per session to bind identity — no per-call token) and `/mcp/analytics` (15 read/analytics
  tools; no auth). URLs: `http://localhost:3005/mcp/...` from host, `http://social-network:3000/mcp/...`
  inside the compose network.
- **Python conventions**: flat `requirements.txt` per service, unpinned, `python:3.11-slim`. Existing
  agents already list `langchain`, `chromadb`, `python-dotenv`. Config via `python-dotenv` + env vars.
- **LLM defaults**: Claude provider defaults to `claude-haiku-4-5` ($1/$5 per 1M tokens) — the fast,
  low-cost tier, a good default for the many simulated persona agents. A developer can point the same
  config at a stronger model (`claude-sonnet-5`, `claude-opus-4-8`) or the Gemini provider. To keep
  behaviour uniform across Claude models, the Claude path does not send `temperature` (it is rejected
  by Opus 4.8 / Sonnet 5 anyway); `temperature` is only forwarded to Gemini.
- **Monitor UI**: a terminal **live dashboard** (via `rich`), backed by a structured metrics object
  so a web UI could consume the same data later.

## Proposed structure

```
modular-agent/
  PLAN.md                   # this file
  README.md                 # what it is, the 5 modules, how to configure + run the demo
  requirements.txt          # langchain, langchain-anthropic, langchain-google-genai,
                            # langchain-mcp-adapters, mcp, chromadb, python-dotenv, rich, pydantic, pytest
  .env.example              # LLM_PROVIDER, ANTHROPIC_API_KEY, GOOGLE_API_KEY, MCP base URLs, token cap
  modular_agent/
    __init__.py
    config.py               # AgentConfig (pydantic): provider, model, api keys, mcp servers+allowlist,
                            #   token cap, max iterations. Loaded from env + explicit overrides.
    llm/factory.py          # build_llm(config) -> ChatAnthropic | ChatGoogleGenerativeAI (Module 1)
    tools/mcp_client.py     # connect to MCP servers over streamable_http, keep a persistent session,
                            #   call `login` on /mcp/social, load tools, FILTER by allowlist (Module 2)
    events/event.py         # WorldEvent pydantic model (id, type, source, payload, ts)
    events/inbox.py         # EventInbox: inject()/get() API for external producers (Module 3)
    persona/persona.py      # Persona = Identity + Voice + Objectives + Guardrails -> system prompt
    memory/working.py       # per-invoke conversation buffer            } Module 4 (internal logic):
    memory/episodic.py      # append-only log of events + actions/decisions }  persona + memory
    memory/semantic.py      # chromadb-backed long-term retrievable store  }  (semantic opt-in)
    memory/retrieval.py     # policy: what to pull into a given invoke     }
    loop/agent.py           # ModularAgent orchestrator (the loop, Module 4)
    monitor/pricing.py      # per-model $/Mtok table (claude-opus-4-8, sonnet-5, haiku-4-5, gemini)
    monitor/metrics.py      # InvokeMetrics + RunMetrics dataclasses + budget state
    monitor/callback.py     # LangChain callback: track tokens/steps/tools; ENFORCE hard cap (Module 5)
    monitor/dashboard.py    # rich live terminal dashboard reading RunMetrics
  examples/demo_customer_agent.py   # configures the baseline into a loyal-customer persona + runs it
  tests/                    # unit tests with mocked LLM + mocked MCP tools
```

## Module details

**1. LLM provider** — `llm/factory.py` reads `config.provider` (`claude` | `gemini`) and returns a
LangChain chat model: `ChatAnthropic` (default `claude-haiku-4-5`) or `ChatGoogleGenerativeAI`. API
key + model id come from `AgentConfig`. Provider SDKs are imported lazily so installing only the
provider you use is enough. Both expose the same `.bind_tools`/`.ainvoke` interface, so the loop is
provider-agnostic. `temperature` is only forwarded to Gemini.

**2. MCP tool allowlist** — `tools/mcp_client.py` uses `langchain-mcp-adapters` over
`streamable_http`. Because `/mcp/social` binds identity to the session, it opens a **persistent
session**, calls the `login` tool first, then `load_mcp_tools` on that same session. The developer
declares an allowlist per server in config (`{server: [tool_names]}` or `"*"`); loaded tools are
filtered to that set before being bound to the LLM. Analytics needs no login.

**3. World-event injection** — `events/event.py` defines a `WorldEvent`; `events/inbox.py` exposes a
thread-safe `EventInbox.inject(event)` plus an optional subscriber hook, so the Event Generator or any
external program can push events without knowing the agent's internals. The loop pulls from the inbox.

**4. Internal logic** — split into persona, memory, and the loop:
- **Persona** (`persona/persona.py`): `Identity`, `Voice`, `Objectives`, `Guardrails` sub-parts that
  render into a system prompt. Guardrails carry the no-leakage / stay-in-character rules.
- **Memory**: `working` (this invoke), `episodic` (append-only event+action log — doubles as decision
  logging), `semantic` (chromadb long-term, opt-in), and a `retrieval` policy. Each layer is
  independently toggleable via config.
- **The loop** (`loop/agent.py`, `ModularAgent`): explicit stages —
  **Perceive → Recall → Reason → Act → Reflect → Respond**. The Reason↔Act inner loop uses LangChain
  1.x's `create_agent` (the supported v1 tool-calling agent — LangGraph-backed under the hood) with
  the allowlisted MCP tools; the surrounding stages are our own methods so each is testable and
  overridable. _(Note: LangChain 1.x removed the older `create_tool_calling_agent` / `AgentExecutor`,
  so `create_agent` is the current path rather than a hand-written graph.)_

**5. Token limits + monitoring** — a LangChain callback handler (`monitor/callback.py`) reads
`usage_metadata` on each LLM response to accumulate input/output tokens, and **enforces the hard cap
by aborting before a call once the cumulative budget is spent** (not after the fact). `monitor/metrics.py`
tracks per-invoke and cumulative stats; `monitor/dashboard.py` renders a `rich` live terminal
dashboard showing: per-invoke + cumulative **token usage** (prompt/completion split), **cost
estimate** and **budget remaining** (with a warn threshold), **loop-step count** (LLM calls /
iterations, to catch runaway loops), **tool-call metrics** (which MCP tools, counts, success/failure),
**latency** per invoke and per tool call, **error/refusal tracking**, and a **per-invoke trace**
(run id + ordered timeline).

## Demo

`examples/demo_customer_agent.py`: configures the baseline as a loyal-customer persona, allowlists a
small set of `/mcp/social` tools (e.g. `login`, `get_global_feed`, `search`, `create_post`,
`add_comment`) plus a couple of `/mcp/analytics` reads, injects one sample world event (e.g. a
contamination rumor), runs the loop, and shows the live terminal dashboard.

## Verification

1. **Unit tests** (`pytest` in `modular-agent/tests/`): mock the LLM and MCP tools — verify the
   allowlist filters tools correctly, the loop calls stages in order, episodic memory records
   actions, and the token callback aborts when the cap would be exceeded.
2. **Live end-to-end** (requires the social network running): `docker compose up social-network`
   (from repo root), then from `modular-agent/` with a virtualenv and a real `ANTHROPIC_API_KEY` in
   `.env`, run `python examples/demo_customer_agent.py`. Confirm the agent logs into `/mcp/social`,
   posts/comments in reaction to the injected event, and the rich dashboard shows token usage, cost,
   budget, steps, and tool calls updating live. Point the MCP base URL at `http://localhost:3005`.
3. **Cap check**: set a very low token budget in config and confirm the run aborts cleanly with a
   clear message instead of overrunning.

## Out of scope (this task)

- Wiring `customer-agent` / `influencer-agent` onto the baseline, and any `docker-compose.yml` /
  Dockerfile changes (a Dockerfile can be added later for compose parity).
- Changes to `social_network` or the MCP servers.

# modular-agent — Task Tracker

Living checklist for building the modular agent baseline. Maintained throughout the session.
Statuses: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked.

_Last updated: 2026-07-09_

## Legend / conventions
- Each task maps to a file or module described in [PLAN.md](./PLAN.md).
- Keep tasks small and verifiable. Update status as work lands.

---

## 0. Scaffolding
- [x] Create package skeleton (`modular_agent/` with `__init__.py` files)
- [x] `requirements.txt` (unpinned, per repo convention)
- [x] `.env.example` (provider, keys, MCP URLs, token budget)
- [x] `README.md` (entry point pointing to the developer guide)

## 1. LLM provider (Module 1)
- [x] `config.py` — `AgentConfig` + `MCPServerConfig` (pydantic) + `from_env`
- [x] `llm/factory.py` — `build_llm()` for Claude + Gemini (lazy provider imports)

## 2. MCP tool allowlist (Module 2)
- [x] `tools/mcp_client.py` — persistent streamable-http session, `login`, load tools
- [x] allowlist filtering (`{server: [tool_names]}` / `"*"`) with unknown-name warnings

## 3. World-event injection (Module 3)
- [x] `events/event.py` — `WorldEvent` model + `render()`
- [x] `events/inbox.py` — thread-safe `EventInbox` + subscriber hook

## 4. Internal logic (Module 4)
- [x] `persona/persona.py` — Identity / Voice / Objectives / Guardrails → system prompt
- [x] `memory/working.py` — per-invoke conversation buffer
- [x] `memory/episodic.py` — append-only event/action log (decision logging)
- [x] `memory/semantic.py` — chromadb-backed long-term store (opt-in, lazy import); requires an
      injected embedder or explicit `use_default_embedder=True` (no silent model download)
- [x] `memory/retrieval.py` — retrieval policy (what to pull per invoke)
- [x] `loop/agent.py` — `ModularAgent` orchestrator (Perceive→Recall→Reason→Act→Reflect→Respond)

## 5. Token limits + monitoring (Module 5)
- [x] `monitor/pricing.py` — per-model $/Mtok table + cost estimate
- [x] `monitor/metrics.py` — `InvokeMetrics` / `RunMetrics` + budget state
- [x] `monitor/callback.py` — token/step/tool tracking + hard-cap enforcement
- [x] `monitor/dashboard.py` — `rich` live terminal dashboard (ASCII-safe)

## 6. Demo + tests
- [x] `examples/demo_customer_agent.py` — loyal-customer persona vs. one injected event
- [x] `tests/` — allowlist filtering, stage ordering, episodic recording, budget abort

## 7. Verification
- [x] Unit tests pass (`pytest`) — 17 passing, offline (mocked LLM + MCP; semantic uses a fake embedder)
- [x] Cap-abort check with a low token budget (`test_budget.py`, `test_loop.py`)
- [!] Live end-to-end against `social-network` — **blocked**: needs a real API key
      (per CLAUDE.md, not used without explicit permission). Code supports it; run deferred.

---

## Notes / decisions
- Monitor surfaces metrics via a **terminal live dashboard** (rich), backed by a structured
  metrics object so a web UI could consume it later. Dashboard glyphs are ASCII-only for
  cross-console (incl. legacy Windows cp1252) safety.
- LLM default: **`claude-haiku-4-5`** (fast/cheap tier); swappable to `claude-sonnet-5`,
  `claude-opus-4-8`, or the Gemini provider via config.
- `temperature` is never sent on the Claude path (only forwarded to Gemini).
- **Loop implementation:** LangChain 1.x removed `AgentExecutor` / `create_tool_calling_agent`.
  The Reason↔Act loop now uses `langchain.agents.create_agent` (the supported v1 tool-calling
  agent, LangGraph-backed under the hood). Our Perceive/Recall/Reflect/Respond stages still wrap it.
- Nothing outside `modular-agent/` changed this task cycle (demo only).

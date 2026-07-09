# modular-agent

A reusable **LangChain (Python) agent baseline** for the BitriX / HappyTuna crisis simulation.
Build a concrete agent (customer, influencer, CEO, …) by *configuring* this baseline and shaping its
persona and memory — not by rewriting the plumbing each time.

Five configurable modules:

1. **LLM provider** — Claude (default `claude-haiku-4-5`) or Gemini, via config + API key.
2. **MCP tool allowlist** — declare which MCP servers and tool names the agent may use.
3. **World-event injection** — push `WorldEvent`s in via an `EventInbox`.
4. **Internal logic** — persona (role/tone/voice/guardrails) + memory (working/episodic/semantic) +
   an explicit reasoning loop (Perceive → Recall → Reason → Act → Reflect → Respond).
5. **Token limits + monitoring** — a hard token budget plus a live terminal dashboard.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set keys only if you have permission to use them
pytest                      # offline unit tests (mocked LLM + MCP)
```

- **Full usage guide (with diagrams):** [`docs/DEVELOPER_GUIDE.md`](./docs/DEVELOPER_GUIDE.md)
- **Design:** [`PLAN.md`](./PLAN.md) · **Progress:** [`TASKS.md`](./TASKS.md) · **Contributor notes:** [`CLAUDE.md`](./CLAUDE.md)
- **Worked example:** [`examples/demo_customer_agent.py`](./examples/demo_customer_agent.py)

> Semantic (chromadb) memory is opt-in and added last; working + episodic memory are on by default.
> Running the live demo needs the `social-network` service up and — for a real model call — an API
> key you've been explicitly cleared to use.

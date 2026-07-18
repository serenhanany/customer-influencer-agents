# Customer Agent

A standalone Python service that simulates a customer persona reacting to events during the
HappyTuna food-safety crisis. It is built on the
[NVIDIA NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) (`nvidia-nat`), calls
a NIM-hosted model through [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails), and —
when a persona decides to complain — files a **real** ticket in the separate Customer Support
system, over MCP. It never touches that system's database directly.

## Architecture

This service plays both sides of MCP: it's an **MCP server** (exposing itself as one tool,
`customer_agent_react`) and, internally, an **MCP client** (consuming the Customer Support
system's tools).

```
caller (you, curl-equivalent via an MCP client, or a future
        event-driven poller -- see "What's not done yet" below)
        |
        |  MCP tool call: customer_agent_react({persona_id, event})
        v
customer-agent (this service)  --  nat mcp serve --tool_names customer_agent_react
  register.py: customer_agent_decision
    1. loads the persona + its in-memory history (personas.py / personas.yaml)
    2. builds a prompt (system_prompt.py) and calls a NIM model
       THROUGH NeMo Guardrails (guardrails_config/) -- input rail checks the
       event isn't a jailbreak, output rail checks the JSON is well-formed
       and the response stays in character
    3. if the decision is "open_support_ticket", calls the MCP-discovered
       create_ticket tool
        |
        v
customer-support-mcp (../Customer_Support_System)  --  real SQLite-backed tickets
```

There is currently **no** REST endpoint (`/generate`, `/docs`, etc.) — that's a deliberate
change from an earlier version of this service. `nat mcp serve` speaks the MCP protocol only.
See "Calling it directly" below for how to actually invoke it.

## Files

| File | What it is |
|---|---|
| `register.py` | The actual decision logic: builds the prompt, calls the guarded LLM, parses the JSON decision, files a ticket if needed, updates in-memory persona state. Registered as the NAT function `customer_agent_decision`. |
| `personas.py` / `personas.yaml` | Persona data (attributes, description, `customer_id`) and its loader. Edit the YAML to tune personas -- no code changes needed. |
| `system_prompt.py` | The full system prompt sent to the LLM: objectives, personality rules, decision process, and the required JSON output schema. |
| `guardrails_config/config.yml`, `prompts.yml` | NeMo Guardrails config: which model to use (NIM), and the input/output check prompts (blocks jailbreaks, off-topic input, malformed output, and character breaks). |
| `workflow.yml` | NAT's workflow config: wires the `customer_support` MCP function group (the real Customer Support MCP server) to the `customer_agent_decision` function. |
| `pyproject.toml` | Makes this an installable package and registers `register.py` with NAT's plugin discovery via `[project.entry-points."nat.components"]` -- required for `nat mcp serve` to find it at all. |
| `Dockerfile` | `python:3.11-slim`, `pip install .` (not `-r requirements.txt` -- see above), then `nat mcp serve --tool_names customer_agent_react`. |
| `test_workflow.py` | In-process test of the decision logic against a **real** Customer Support MCP server, with the LLM call mocked. |
| `test_packaging.py` | Regression test for a real packaging bug (see "Testing" below) -- installs into a throwaway venv and checks `personas.yaml` still resolves correctly. |

## Personas

Defined in `personas.yaml`, loaded by `personas.py`. Each has a `customer_id` (matches a record
the Customer Support system understands) and six attributes, each `0.0`-`1.0`:

| Persona | Loyalty | Trust | Risk sensitivity | Price sensitivity | Complaint tendency | Forgiveness |
|---|---|---|---|---|---|---|
| `loyal_customer` | 0.95 | 0.9 | 0.3 | 0.1 | 0.1 | 0.9 |
| `vocal_complainer` | 0.2 | 0.35 | 0.65 | 0.4 | 0.95 | 0.2 |
| `price_sensitive` | 0.35 | 0.55 | 0.2 | 0.95 | 0.25 | 0.55 |
| `risk_sensitive` | 0.5 | 0.6 | 0.98 | 0.2 | 0.55 | 0.3 |
| `skeptical_customer` | 0.1 | 0.15 | 0.7 | 0.5 | 0.7 | 0.1 |

The system prompt (`system_prompt.py`) instructs the model that these attributes must actually
drive the decision -- e.g. a high `complaint_tendency` persona should complain far more readily
than a low one. Persona **memory** (`trust_score`, `past_decisions`) is kept in an in-memory
dict, keyed by `persona_id` -- see "What's not done yet" for its limitation.

## Guardrails

Every call goes through NeMo Guardrails, not directly to the model:

- **Input rail** (`self_check_input`) blocks: instructions to ignore the persona/system prompt,
  attempts to extract the system prompt, requests to role-play as something else, input with no
  plausible connection to HappyTuna/food safety, or abusive content.
- **Output rail** (`self_check_output`) blocks: non-JSON output, missing required fields, an
  `action` outside the fixed enum, reasoning that invents facts not present in the event, or
  output that breaks character (e.g. "as an AI language model...").

This matters here specifically because a passing decision can trigger a **real** side effect (a
ticket in the Customer Support system) -- the guardrails are the thing standing between
untrusted `event` input and that real system.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `NVIDIA_API_KEY` | — | **Required.** Used by NeMo Guardrails' NIM engine (`guardrails_config/config.yml`) to actually call the model. Get one at https://build.nvidia.com. Set it in the repo-root `.env` (shared by every service via `env_file: .env` in `docker-compose.yml`). |
| `CUSTOMER_SUPPORT_MCP_URL` | `http://customer-support-mcp:8010/mcp` | Where the real Customer Support MCP server is. The default assumes Docker Compose's internal DNS; override to `http://localhost:8010/mcp` when running this service outside Docker against a Dockerized Customer Support system. |
| `PERSONAS_CONFIG_PATH` | `/app/personas.yaml` (set in the Dockerfile) | Where `personas.py` reads persona data from. Needed explicitly because once this package is `pip install`-ed (not run as loose script files), `personas.py`'s own directory is inside `site-packages`, not `/app` -- see "Testing" below. |

## Running with Docker Compose (recommended)

From the repo root:

```bash
cp .env.example .env   # fill in NVIDIA_API_KEY
docker compose up --build customer-support-mcp customer-support-api customer-agent
```

This also starts the Customer Support MCP server and its backing API/DB, since `customer-agent`
depends on the MCP server being reachable at `CUSTOMER_SUPPORT_MCP_URL`.

### Calling it directly

There's no browser-friendly URL -- you need an MCP client. Minimal example (`mcp` is already a
transitive dependency of `nvidia-nat-mcp`, so this works from inside the container, or locally
if you `pip install mcp`):

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://localhost:8001/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("customer_agent_react", {
                "persona_id": "vocal_complainer",
                "event": "HappyTuna recalls batch 4471 after a customer found a metal fragment in a can.",
            })
            print(result.content[0].text)

asyncio.run(main())
```

(Port `8001` is the host-mapped port from `docker-compose.yml`; inside the Docker network, or
inside the container itself, it's `8000`.)

## Running locally without Docker

```bash
cd customer-agent
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate
pip install -e .
export NVIDIA_API_KEY=...                         # https://build.nvidia.com
export CUSTOMER_SUPPORT_MCP_URL=http://localhost:8010/mcp
nat mcp serve --config_file workflow.yml --host 0.0.0.0 --port 8000 --tool_names customer_agent_react
```

(The Customer Support MCP server must already be running separately -- see
`../Customer_Support_System/README.md`.)

## Testing

Two test files, covering different things:

- **`python test_workflow.py`** -- runs the decision logic in-process, against a **real**
  running Customer Support MCP server, with only the LLM call mocked (no `NVIDIA_API_KEY`
  needed). It does `import register` directly, which means it does **not** exercise NAT's
  plugin/entry-point discovery -- it can't catch a packaging regression.
- **`python test_packaging.py`** -- the packaging regression test. It installs this package
  into a throwaway virtualenv exactly the way the Dockerfile does (`pip install .`, no editable
  install), then confirms `personas.yaml` still resolves correctly. This exists because of a
  real bug found while testing: a non-editable install copies `personas.py` into
  `site-packages`, separate from `personas.yaml`, which only lives in `/app` -- so
  `Path(__file__).parent / "personas.yaml"` pointed at the wrong place and `get_persona()` threw
  `FileNotFoundError`, but *only* under a real install, never when running the script directly
  from this folder (which is why `test_workflow.py` never caught it). Fixed via the
  `PERSONAS_CONFIG_PATH` env var set in the Dockerfile. This test proves the failure still
  reproduces if that env var were ever removed, then proves it's fixed.

Neither test makes a real call to the NIM model. To verify that (and the real
`nat mcp serve` + `--tool_names` + entry-point-discovery path end to end), build and run the
actual image and call it as a real MCP client, e.g. the snippet under "Calling it directly"
above, run from inside the container:

```bash
docker compose up --build customer-support-mcp customer-support-api customer-agent
docker cp your_test_script.py customer-agent:/tmp/test.py
docker exec customer-agent python /tmp/test.py
```

## What's not done yet

- **No autonomous driver.** Unlike `influencer-agent` (which has `poller.py` continuously
  polling `social_network` and calling its workflow automatically), nothing currently calls
  `customer_agent_react` on its own. It sits ready, waiting to be invoked. If this agent should
  react to crisis events automatically, something analogous to `influencer-agent`'s poller
  needs to be built -- an MCP client that watches for events and calls this tool.
- **Persona memory resets on restart.** `trust_score` and `past_decisions` live in a plain
  Python dict in `register.py` (`_memory`), not a database. The upgrade path (swap for a small
  SQLite table keyed by `persona_id`, same pattern the Customer Support system used) is noted
  directly in `register.py`'s bottom comment and doesn't require changing the calling code.
- Only `customer_agent_react` is exposed via MCP (`--tool_names` in the Dockerfile). The
  Customer Support tools this agent consumes internally are deliberately **not** re-exposed --
  they're already served directly by `customer-support-mcp`.

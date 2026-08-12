# CEO Agent — MCP Gateway

Connects to the three MCP servers the other teams run (Customer Support, Social
Network, Social Analytics) and exposes a filtered tool set per role. It injects the
caller's identity server-side, holds back irreversible public actions in dry run,
and audits every call. It makes no decisions — the loop, prompts, and model are
yours.

## Setup

```bash
# macOS ships python3, not python
cp social_network/.env.example social_network/.env      # compose fails without it
docker compose up -d social-network customer-support-mcp

python3 -m venv .venv && source .venv/bin/activate
pip install -r ceo_agent/requirements.txt

pytest                                          # 53 passed, 1 deselected
python3 ceo_agent/cli.py check --profile local  # 3/3 connected, 25 visible
```

`Customer_Support_System/requirements.txt` must pin `mcp==1.29.0`. Unpinned, pip
installs 2.0.0 and their container crashes on startup.

## Usage

```python
from gateway.catalog import build_catalog
from gateway.connection import GatewayConnections
from gateway.registry import load_registry
from gateway.router import Router

async with GatewayConnections(load_registry(profile="local")) as connections:
    await connections.connect_all()
    catalog = await build_catalog(connections.sessions)
    router = Router(connections, catalog, role="ceo", dry_run=True)

    # A silent CEO and one that couldn't reach the platform must not look alike.
    for status in router.get_status():
        if not status.connected:
            print(status.server_id, status.skipped_reason)
    tools = router.get_langchain_tools()   # StructuredTools, filtered to the role
    agent = create_agent(model, tools, system_prompt=YOUR_BRIEF)

    result = await router.call_tool("support.patch_ticket", {
        "ticket_id": "TCK-00042", "status": "escalated",
    })
```

`dry_run=True` answers `create_post` and `add_comment` without sending them; reads
and ticket writes still execute. Keep it on until the agent should speak in public.
Your brief needs no tool list — the model reads the schemas. `Router` never raises:
check `result.ok`. `langchain`/`langgraph` are not dependencies of this package.

## What the CEO can do

25 of 42 tools are visible to role `ceo`: the support queue, the analytics
surface, and public reads. Three of them write:

| Tool | |
|---|---|
| `social.create_post` | **irreversible, public** — no delete tool exists anywhere |
| `social.add_comment` | **irreversible, public** — joins a thread, inherits its audience |
| `support.patch_ticket` | respond, escalate, reassign |

Hidden: `run_analysis` and `set_ai_analysis` (they mutate the numbers the CEO is
scored against), `social.login` and `set_account_type` (identity), and
`support.create_ticket` (fabricating a complaint). `customer-agent` is not in the
registry at all — its one tool invents a customer *and* files a real ticket.

## Adding an MCP server

Three edits, no code:

1. a block in `mcp_servers.yaml`
2. its tools classified in `TOOL_ACCESS` (`gateway/catalog.py`)
3. a grant in `roles.yaml`

```yaml
  - id: email
    urls:
      docker: http://email-service:8020/mcp
      local: http://localhost:8020/mcp
```

A live tool missing from `TOOL_ACCESS` aborts the catalog build, on purpose — an
unassessed capability must not reach the agent by default. Forgetting to *grant*
one just leaves it hidden. Update `RECORDED_*` in `tests/test_integration.py`.

## Commands

```bash
python3 ceo_agent/cli.py check --profile local       # connect, catalogue, policy summary
python3 ceo_agent/cli.py dump  --profile local       # the surface, as the model sees it (--all, --json)
pytest ceo_agent/tests/test_unit.py                  # no network, no Docker
pytest ceo_agent/tests/test_integration.py           # needs the servers; skips cleanly if down
```

## Gotchas

- `--profile local` is required off-compose; the default `docker` profile uses
  compose hostnames that don't resolve from your host.
- `pytest -m writes` creates and patches a real ticket. Off by default.
- A whole-server allow (`analytics.*`) sweeps in that server's writes. The explicit
  `deny` entries in `roles.yaml` are load-bearing — deleting one silently grants
  operator powers.
- `streamablehttp_client` is deprecated in mcp 1.29.0 and gone in 2.0. Migrating
  means owning an `httpx.AsyncClient` to keep per-server timeouts.
- `ENUM_INJECTIONS` in `router.py` hand-copies
  `Customer_Support_System/models.py:7-34`; nothing fails if they add a member.

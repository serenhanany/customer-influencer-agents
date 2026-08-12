"""Integration tests. These need the live MCP servers.

    docker compose up -d social-network customer-support-mcp
    pytest ceo_agent/tests/test_integration.py

Skipped cleanly, with instructions, when nothing is reachable -- see the
`gateway` fixture in conftest.py. Partial connectivity is not skipped: a server
that is down when the others are up is a real failure, and
`test_all_servers_connect` is meant to catch it.

Read-only by default: no tickets, no posts. The one write test is marked
`writes` and deselected by pytest.ini's addopts. To run it:

    pytest ceo_agent/tests/test_integration.py -m writes

It creates a ticket and patches it, leaving rows in the real Customer Support
database. That is the only way to prove the injected actor reaches the activity
log, which is why it exists and why it is off by default.
"""

from __future__ import annotations

import json

import pytest

from gateway.connection import call_tool as raw_call
from gateway.router import Router

pytestmark = pytest.mark.integration


# The surface as recorded when this was written. These four numbers are the only
# things here that need updating when a server is added or a team ships a tool --
# see the invariant tests below, which never do. A failure here is either an
# upstream change worth knowing about, or an intended change worth recording.
RECORDED_SERVERS = 3
RECORDED_TOOLS = 42
RECORDED_VISIBLE = 25
RECORDED_HIDDEN = RECORDED_TOOLS - RECORDED_VISIBLE  # 17


@pytest.fixture()
def router(gateway, tmp_path) -> Router:
    """A CEO router writing its audit log somewhere disposable."""
    return Router(gateway.connections, gateway.catalog, role="ceo",
                  audit_path=tmp_path / "audit.jsonl")


@pytest.fixture()
def dry_router(gateway, tmp_path) -> Router:
    return Router(gateway.connections, gateway.catalog, role="ceo",
                  dry_run=True, audit_path=tmp_path / "audit.jsonl")


def audit_records(path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# ---------------------------------------------------------------------------
# connection
# ---------------------------------------------------------------------------


def test_all_servers_connect(gateway):
    statuses = gateway.statuses
    down = [s for s in statuses if not s.connected]

    assert not down, "not connected: " + "; ".join(
        f"{s.server_id} ({s.skipped_reason})" for s in down
    )
    assert len(statuses) == RECORDED_SERVERS


def test_social_login_ran_and_bound_an_identity(gateway):
    """Writes 401 until login populates the session's closure state."""
    social = next(s for s in gateway.statuses if s.server_id == "social")

    assert social.login_attempted is True
    assert social.login_ok is True
    assert social.identity, "login returned no token; later writes would be unauthored"


def test_servers_with_no_login_report_not_applicable(gateway):
    analytics = next(s for s in gateway.statuses if s.server_id == "analytics")

    # None means "nothing configured", not "ran and failed".
    assert analytics.login_attempted is False
    assert analytics.login_ok is None


# ---------------------------------------------------------------------------
# catalog
# ---------------------------------------------------------------------------


def test_catalog_size_matches_the_recorded_surface(gateway):
    assert len(gateway.catalog) == RECORDED_TOOLS
    assert len(gateway.catalog.server_ids) == RECORDED_SERVERS


def test_every_live_tool_is_classified(gateway):
    """Invariant. Needs no update when a server is added -- build_catalog raises."""
    assert all(entry.access in ("read", "write", "public_write") for entry in gateway.catalog)


def test_colliding_names_are_namespaced(gateway):
    """The three names that exist on two servers each, with different schemas."""
    for name in ("search", "get_post", "get_hashtag_posts"):
        social = gateway.catalog.get(f"social.{name}")
        analytics = gateway.catalog.get(f"analytics.{name}")
        assert social is not None, f"social.{name} missing"
        assert analytics is not None, f"analytics.{name} missing"
        assert social.tool_name == analytics.tool_name == name


def test_the_two_irreversible_tools_are_tagged_public_write(gateway):
    public = {e.qualified_name for e in gateway.catalog.by_access("public_write")}

    assert public == {"social.create_post", "social.add_comment"}


# ---------------------------------------------------------------------------
# policy
# ---------------------------------------------------------------------------


def test_ceo_surface_matches_the_recorded_size(router, gateway):
    visible = router.get_tools()

    assert len(visible) == RECORDED_VISIBLE
    assert len(gateway.catalog) - len(visible) == RECORDED_HIDDEN


def test_operator_controls_are_hidden(router):
    visible = {entry.qualified_name for entry in router.get_tools()}

    # Instruments the CEO is scored by, identity rebinding, and ticket fabrication.
    for name in ("analytics.run_analysis", "analytics.set_ai_analysis",
                 "social.login", "social.set_account_type", "support.create_ticket"):
        assert name not in visible, f"{name} is visible to the CEO"


def test_no_dead_rules(router, gateway):
    """Invariant. Fails when a team renames a tool roles.yaml still names."""
    from gateway.policy import build_policy

    problems = build_policy("ceo").validate_against_catalog(gateway.catalog)

    assert problems == [], "; ".join(problems)


def test_langchain_tools_match_the_visible_surface(router):
    tools = router.get_langchain_tools()

    assert len(tools) == len(router.get_tools())
    assert all("." not in t.name for t in tools)
    names = {t.name for t in tools}
    assert "analytics__run_analysis" not in names


# ---------------------------------------------------------------------------
# router: real calls
# ---------------------------------------------------------------------------


def _first_argless_read(router) -> str:
    """A visible read tool that needs no arguments, preferring the cheap ones."""
    specs = {s["name"]: s for s in router.get_tools_for_llm()}
    preferred = ["analytics.get_analysis_status", "analytics.get_overview",
                 "social.get_global_feed", "social.get_trending_hashtags"]
    candidates = preferred + sorted(specs)

    for name in candidates:
        spec = specs.get(name)
        if spec and not spec["input_schema"].get("required"):
            entry = next(e for e in router.get_tools() if e.qualified_name == name)
            if entry.access == "read":
                return name
    pytest.skip("no argument-free read tool in the visible surface")


async def test_a_real_read_succeeds(router):
    name = _first_argless_read(router)

    result = await router.call_tool(name, {})

    assert result.ok is True, f"{name} failed: {result.error}"
    assert result.is_error is False
    assert result.text is not None or result.data is not None
    assert result.elapsed_ms > 0


async def test_denied_call_returns_failure_and_never_dispatches(router, tmp_path):
    result = await router.call_tool("analytics.run_analysis", {})

    assert result.ok is False
    assert "not available to role 'ceo'" in result.error
    assert result.qualified_name == "analytics.run_analysis"

    end = [r for r in audit_records(tmp_path / "audit.jsonl") if r["event"] == "call_end"]
    assert end[-1]["outcome"] == "denied"


async def test_denied_call_is_blocked_under_either_spelling(router):
    """The LangChain spelling resolves to the same name, so it is denied too."""
    result = await router.call_tool("analytics__run_analysis", {})

    assert result.ok is False


async def test_unknown_name_returns_failure(router, tmp_path):
    """Note the server: roles.yaml grants "support.*", so this name satisfies the
    policy and is stopped by the catalog check instead. The error must say so
    rather than blaming the connection."""
    result = await router.call_tool("support.delete_everything", {})

    assert result.ok is False
    assert "No such tool" in result.error
    assert "not connected" not in result.error

    end = [r for r in audit_records(tmp_path / "audit.jsonl") if r["event"] == "call_end"]
    assert end[-1]["outcome"] == "unknown_tool"


async def test_dry_run_does_not_reach_the_server(dry_router, tmp_path):
    args = {"content": "pytest dry run -- this must never be published"}

    result = await dry_router.call_tool("social.create_post", args)

    assert result.ok is True
    assert result.data == {"dry_run": True, "would_send": args}
    # Nothing came back from a server, because nothing was sent.
    assert result.text is None
    assert result.is_error is False

    end = [r for r in audit_records(tmp_path / "audit.jsonl") if r["event"] == "call_end"]
    assert end[-1]["outcome"] == "dry_run"


async def test_dry_run_still_lets_reads_through(dry_router):
    name = _first_argless_read(dry_router)

    result = await dry_router.call_tool(name, {})

    assert result.ok is True
    assert result.data != {"dry_run": True}


def test_get_status_reports_every_configured_server(router):
    statuses = router.get_status()

    assert len(statuses) == RECORDED_SERVERS
    assert {s.server_id for s in statuses} == {"support", "analytics", "social"}


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


async def test_every_call_writes_a_start_and_an_end(router, tmp_path):
    path = tmp_path / "audit.jsonl"
    name = _first_argless_read(router)

    await router.call_tool(name, {})
    await router.call_tool("analytics.run_analysis", {})       # denied
    await router.call_tool("support.delete_everything", {})    # unknown

    records = audit_records(path)
    starts = [r for r in records if r["event"] == "call_start"]
    ends = [r for r in records if r["event"] == "call_end"]

    assert len(starts) == len(ends) == 3
    # Paired by call_id, one start per end.
    assert {r["call_id"] for r in starts} == {r["call_id"] for r in ends}
    assert all(r["role"] == "ceo" for r in records)
    # The two calls that never dispatched are recorded just like the one that did.
    assert {r["outcome"] for r in ends} == {"ok", "denied", "unknown_tool"}


async def test_audit_records_the_access_level_and_timing(router, tmp_path):
    name = _first_argless_read(router)

    await router.call_tool(name, {})

    end = [r for r in audit_records(tmp_path / "audit.jsonl") if r["event"] == "call_end"][-1]
    assert end["access"] == "read"
    assert end["ok"] is True
    assert end["elapsed_ms"] > 0
    assert "timestamp" in end


# ---------------------------------------------------------------------------
# writes -- off by default: `pytest ceo_agent/tests/test_integration.py -m writes`
# ---------------------------------------------------------------------------


@pytest.mark.writes
async def test_actor_is_injected_as_ceo_on_a_real_ticket(gateway, router, tmp_path):
    """Proves identity injection reaches the Customer Support activity log.

    Leaves a ticket and its log entries in the real database. The ticket is
    created through the raw connection layer, not the router, because
    support.create_ticket is denied to the CEO -- fabricating a complaint is
    exactly what the policy forbids. That makes this a test harness acting as the
    environment, not the agent doing something it is not allowed to do.
    """
    session = gateway.connections.session_for("support")
    config = gateway.connections.config_for("support")
    assert session is not None, "support server not connected"

    created = await raw_call(session, config, "create_ticket", {
        "customer_id": "PYTEST-HARNESS",
        "issue_type": "quality",
        "subject": "pytest fixture ticket -- safe to delete",
        "description": "pytest: verifying gateway actor injection. Safe to delete.",
    })
    assert created.ok, f"harness could not create a ticket: {created.error}"
    ticket_id = (created.data or {}).get("ticket_id")
    assert ticket_id, f"no ticket_id in {created.data!r}"

    async def entries() -> list[dict]:
        log = await router.call_tool("support.get_activity_log", {"ticket_id": ticket_id})
        assert log.ok is True, log.error
        return (log.data or {}).get("entries", [])

    # The rows the harness itself produced. Creation is filed under "system"
    # because the harness passes no actor -- that is the upstream default this
    # guarantee exists to override, and it is not what is under test here.
    before = await entries()

    # The agent path: note that `actor` is not passed, and cannot be.
    patched = await router.call_tool("support.patch_ticket", {
        "ticket_id": ticket_id,
        "status": "in_progress",
        "reply_message": "pytest: gateway integration test",
    })
    assert patched.ok is True, patched.error

    after = await entries()
    new_rows = after[len(before):]

    assert new_rows, "the patch produced no activity log entries"
    actors = {row.get("actor") for row in new_rows}
    assert actors == {"ceo"}, (
        f"every row the patch produced should be filed under 'ceo', got {actors}. "
        f"'system' here means identity injection did not apply."
    )

    # And the audit log recorded the injected value, not what the caller sent.
    end = [r for r in audit_records(tmp_path / "audit.jsonl")
           if r["event"] == "call_end" and r["qualified_name"] == "support.patch_ticket"][-1]
    assert end["args"]["actor"] == "ceo"


def test_advertised_schema_hides_actor(router):
    """The other half of the guarantee: the model is never shown the parameter.

    Read-only, so this one runs by default -- only the ticket-writing half above
    is behind the marker.
    """
    spec = next(s for s in router.get_tools_for_llm() if s["name"] == "support.patch_ticket")

    assert "actor" not in spec["input_schema"]["properties"]
    assert "actor" not in spec["input_schema"].get("required", [])
    status = spec["input_schema"]["properties"]["status"]
    branches = [b for b in status.get("anyOf", [status]) if b.get("type") == "string"]
    assert branches and "escalated" in branches[0]["enum"]

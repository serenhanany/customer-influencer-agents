"""Unit tests for gateway_bridge.py's domain-error detection.

    pytest ceo_agent/tests/test_gateway_bridge.py

No network, no Docker, no MCP servers -- see test_agent_loop.py for the same
approach. This is the fix for a real gap found while running the CEO scenario
live: two of the three backend services (internal-chat, Customer_Support_System)
report a business-level failure (bad channel, unknown ticket id) inside a
normally-shaped, transport-successful JSON body instead of MCP's own isError
flag. GatewayToolAdapter.run() used to trust transport success alone, so a
failed chat.send_message or support.get_ticket call was recorded as a
completed step with the failure buried, unread, inside its "successful"
result.

Everything here is about that being caught at the adapter boundary instead.
"""

from __future__ import annotations

import asyncio

from base.tool_base import ToolResult
from gateway_bridge import GatewayToolAdapter, _domain_error

# ---------------------------------------------------------------------------
# _domain_error(): pure function, no fakes needed
# ---------------------------------------------------------------------------


def test_chat_style_failure_is_detected():
    """internal-chat's convention: {"ok": false, "error": {"code", "message"}}."""
    value = {"ok": False, "tool": "chat.send_message",
              "error": {"code": "NOT_FOUND", "message": "No channel 'x'"}}
    assert _domain_error(value) == "No channel 'x'"


def test_support_style_failure_is_detected():
    """Customer_Support_System's convention: a bare {"error": "..."} string."""
    value = {"error": "Ticket 'TCK-999' not found"}
    assert _domain_error(value) == "Ticket 'TCK-999' not found"


def test_error_dict_with_no_message_falls_back_to_json():
    value = {"error": {"code": "X"}}
    assert _domain_error(value) == '{"code": "X"}'


def test_chat_style_success_is_not_a_domain_error():
    value = {"ok": True, "tool": "chat.send_message", "error": None,
              "value": {"message_id": "m1"}}
    assert _domain_error(value) is None


def test_support_style_success_is_not_a_domain_error():
    value = {"id": "TCK-1", "subject": "hi"}
    assert _domain_error(value) is None


def test_a_falsy_error_field_is_not_a_domain_error():
    """A present-but-empty "error" key is how these servers spell "no error" --
    None, "", False, and {} must all read the same as the key being absent."""
    for falsy_error in (None, "", False, {}):
        assert _domain_error({"error": falsy_error}) is None


def test_non_dict_values_are_not_domain_errors():
    """Plain-text tool results and list-shaped results have no "error" key to
    read; the check must not raise on them."""
    assert _domain_error("plain text response") is None
    assert _domain_error([1, 2, 3]) is None
    assert _domain_error(None) is None


# ---------------------------------------------------------------------------
# GatewayToolAdapter.run(): the domain-error check wired into the adapter
# ---------------------------------------------------------------------------


class FakeRouterResult:
    """Stand-in for gateway.models.ToolResult -- the router-level result,
    distinct from base.tool_base.ToolResult which the adapter returns."""

    def __init__(self, ok: bool, data=None, text=None, error: str | None = None) -> None:
        self.ok = ok
        self.data = data
        self.text = text
        self.error = error


class FakeRouter:
    """Scripted stand-in for gateway.router.Router: call_tool always returns
    the one queued result, regardless of name/args."""

    def __init__(self, result: FakeRouterResult) -> None:
        self._result = result

    async def call_tool(self, qualified_name: str, args: dict):
        return self._result


class FakeBridge:
    """Stand-in for GatewayBridge.call(): runs the coroutine to completion
    synchronously instead of dispatching to a background event loop."""

    def __init__(self, router: FakeRouter) -> None:
        self.router = router

    def call(self, coro):
        return asyncio.run(coro)


def make_adapter(router_result: FakeRouterResult, is_read: bool = True) -> GatewayToolAdapter:
    return GatewayToolAdapter(
        bridge=FakeBridge(FakeRouter(router_result)),
        qualified_name="chat.send_message",
        description="send a message",
        input_schema={"type": "object", "properties": {}},
        is_read=is_read,
    )


def test_transport_success_with_chat_style_domain_error_is_reported_as_failure():
    """The run-4 shape: the router says ok, the payload says otherwise."""
    payload = {"ok": False, "tool": "chat.send_message",
               "error": {"code": "NOT_FOUND", "message": "No channel 'operations'"}}
    adapter = make_adapter(FakeRouterResult(ok=True, data=payload))

    result = adapter.run(channel="operations", body="hi")

    assert isinstance(result, ToolResult)
    assert result.ok is False
    assert result.error == "No channel 'operations'"


def test_transport_success_with_support_style_domain_error_is_reported_as_failure():
    payload = {"error": "Ticket 'TCK-000' not found"}
    adapter = make_adapter(FakeRouterResult(ok=True, data=payload))

    result = adapter.run(ticket_id="TCK-000")

    assert result.ok is False
    assert result.error == "Ticket 'TCK-000' not found"


def test_genuine_success_is_returned_as_a_value_not_a_failure():
    payload = {"count": 0, "tickets": []}
    adapter = make_adapter(FakeRouterResult(ok=True, data=payload))

    result = adapter.run()

    assert result.ok is True
    assert result.value == payload


def test_transport_level_failure_still_passes_through_unchanged():
    """A genuine transport failure (server unreachable, denied, unknown tool)
    never reaches _domain_error -- result.ok was already False."""
    adapter = make_adapter(FakeRouterResult(ok=False, error="server unreachable"))

    result = adapter.run()

    assert result.ok is False
    assert result.error == "server unreachable"


def test_domain_error_on_a_write_tool_is_not_idempotent():
    """is_idempotent must still reflect is_read on this path -- a domain error
    on a write tool (e.g. chat.send_message) must not be retried, same as any
    other failure of that tool."""
    payload = {"ok": False, "error": {"message": "No channel 'x'"}}
    adapter = make_adapter(FakeRouterResult(ok=True, data=payload), is_read=False)

    result = adapter.run()

    assert result.ok is False
    assert result.is_idempotent is False


def test_domain_error_on_a_read_tool_is_idempotent():
    payload = {"error": "not found"}
    adapter = make_adapter(FakeRouterResult(ok=True, data=payload), is_read=True)

    result = adapter.run()

    assert result.ok is False
    assert result.is_idempotent is True

"""Offline tests for the SSE front end - no network, no container.

Two ways in, for two reasons:

* Plain request/response endpoints go through httpx's ASGITransport, which is
  the concise way to hit a FastAPI app in-process.
* The SSE stream cannot. ASGITransport awaits the whole ASGI app before it
  returns a response (it buffers `body_parts`, then builds the Response), and a
  stream that stays open never completes - the call just hangs. So `SSEClient`
  below speaks ASGI directly, which also lets a test cancel the connection and
  assert the disconnect cleanup ran.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
from urllib.parse import urlencode

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # noqa: E402

READ_TIMEOUT = 5.0


@pytest.fixture(autouse=True)
def clean_broker():
    """Each test starts with an empty registry - the broker is module state."""
    server.broker._subscribers.clear()
    server._connections.clear()
    yield
    server.broker._subscribers.clear()
    server._connections.clear()


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class SSEClient:
    """An open /subscribe connection, driven straight through the ASGI protocol."""

    def __init__(self, **params) -> None:
        self._query = urlencode(params, doseq=True).encode()
        self._chunks: asyncio.Queue[bytes] = asyncio.Queue()
        self._buffer = ""
        self.status: int | None = None

    async def __aenter__(self) -> "SSEClient":
        started = asyncio.Event()

        async def receive():
            # A real client would eventually send http.disconnect; this one
            # stays connected until the test cancels the task.
            await asyncio.Event().wait()

        async def send(message) -> None:
            if message["type"] == "http.response.start":
                self.status = message["status"]
                started.set()
            elif message["type"] == "http.response.body":
                await self._chunks.put(message.get("body", b""))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/subscribe",
            "raw_path": b"/subscribe",
            "query_string": self._query,
            "root_path": "",
            "headers": [(b"host", b"test")],
            "client": ("127.0.0.1", 1234),
            "server": ("test", 80),
        }

        self._task = asyncio.create_task(server.app(scope, receive, send))
        await asyncio.wait_for(started.wait(), timeout=READ_TIMEOUT)
        return self

    async def __aexit__(self, *exc_info) -> None:
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task

    async def events(self, count: int) -> list[dict]:
        """Read `count` data frames, skipping keepalive comments and separators."""
        out: list[dict] = []

        async def pump() -> None:
            while len(out) < count:
                self._buffer += (await self._chunks.get()).decode()
                while "\n\n" in self._buffer:
                    frame, self._buffer = self._buffer.split("\n\n", 1)
                    if frame.startswith("data:"):
                        out.append(json.loads(frame[len("data:") :].strip()))

        await asyncio.wait_for(pump(), timeout=READ_TIMEOUT)
        return out


async def test_health_and_tags(client):
    assert (await client.get("/health")).json() == {"status": "ok", "subscribers": 0}
    # Derived from CRISIS_FEED, not hardcoded in the server.
    assert (await client.get("/tags")).json() == {
        "tags": ["press", "regulator", "social"]
    }


async def test_subscriber_only_gets_its_tag(client):
    async with SSEClient(tag="press") as stream:
        await client.post("/emit", json={"tag": "social", "text": "not for us"})
        await client.post("/emit", json={"tag": "press", "text": "for us"})

        events = await stream.events(1)

    # The social event was emitted first but must not appear.
    assert [e["text"] for e in events] == ["for us"]
    assert events[0]["tag"] == "press"


async def test_untagged_subscriber_gets_every_tag(client):
    async with SSEClient() as stream:
        await client.post("/emit", json={"tag": "social", "text": "a"})
        await client.post("/emit", json={"tag": "regulator", "text": "b"})

        events = await stream.events(2)

    assert [e["tag"] for e in events] == ["social", "regulator"]


async def test_multiple_tags_on_one_connection(client):
    async with SSEClient(tag=["press", "social"]) as stream:
        await client.post("/emit", json={"tag": "regulator", "text": "skipped"})
        await client.post("/emit", json={"tag": "press", "text": "one"})
        await client.post("/emit", json={"tag": "social", "text": "two"})

        events = await stream.events(2)

    assert [e["text"] for e in events] == ["one", "two"]


async def test_seq_is_shared_across_subscribers(client):
    """The same event needs the same seq everywhere, or a gap can't be spotted."""
    async with SSEClient(tag="press") as first, SSEClient(tag="press") as second:
        await client.post("/emit", json={"tag": "press", "text": "shared"})

        first_events = await first.events(1)
        second_events = await second.events(1)

    assert first_events[0]["seq"] == second_events[0]["seq"]


async def test_disconnect_unsubscribes(client):
    async with SSEClient(tag="press") as stream:
        await client.post("/emit", json={"tag": "press", "text": "hello"})
        await stream.events(1)
        assert (await client.get("/health")).json()["subscribers"] == 1

    # Leaving the context cancels the connection, which must clear the registry -
    # otherwise every dropped client leaks a listener into the broker forever.
    assert server.broker._subscribers == {}
    assert (await client.get("/health")).json()["subscribers"] == 0


async def test_replay_reaches_a_subscriber(client):
    """The scripted feed runs on a worker thread; events must still cross to the loop."""
    async with SSEClient(tag="press") as stream:
        await client.post("/replay", params={"delay": 0})

        # CRISIS_FEED has three "press" briefings: Day 3, Day 7, Day 10.
        events = await stream.events(3)

    assert all(e["tag"] == "press" for e in events)
    assert [e["seq"] for e in events] == sorted(e["seq"] for e in events)
    assert "Day 3" in events[0]["text"]


async def test_slow_subscriber_drops_oldest_not_newest():
    """A backed-up client should keep the latest picture of the crisis."""
    sub = server._Subscriber(queue=asyncio.Queue(maxsize=2))
    for text in ("first", "second", "third"):
        server._offer(sub, json.dumps({"text": text}))

    assert sub.dropped == 1
    kept = [json.loads(sub.queue.get_nowait())["text"] for _ in range(2)]
    assert kept == ["second", "third"]

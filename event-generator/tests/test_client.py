"""Tests for event_client, against a real server on a loopback port.

The client speaks HTTP, so unlike the server tests it can't be driven through an
ASGI shim - httpx's ASGITransport buffers the whole app before returning, which
never finishes for an open stream. Running uvicorn on an ephemeral port keeps
these self-contained (no fixed port, no external network, no API keys) while
still exercising the real socket path the agents will use.
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
import threading
import time

import httpx
import pytest
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # noqa: E402
from event_client import Event, subscribe  # noqa: E402

TIMEOUT = 10.0


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def base_url():
    port = _free_port()
    uv = uvicorn.Server(
        uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=uv.run, daemon=True)
    thread.start()

    deadline = time.time() + TIMEOUT
    while not uv.started:
        if time.time() > deadline:
            raise RuntimeError("uvicorn did not start")
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    uv.should_exit = True
    thread.join(timeout=TIMEOUT)


async def _wait_for_subscriber(base_url: str) -> None:
    """Block until the server reports a live subscriber.

    Without this, a replay can fire before the stream is registered and the test
    waits forever for events that were emitted to nobody.
    """
    async with httpx.AsyncClient() as client:
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            health = (await client.get(f"{base_url}/health")).json()
            if health["subscribers"] >= 1:
                return
            await asyncio.sleep(0.05)
    raise AssertionError("subscriber never registered")


async def _collect(base_url: str, tags: tuple[str, ...], count: int) -> list[Event]:
    events: list[Event] = []
    async for event in subscribe(*tags, url=base_url):
        events.append(event)
        if len(events) >= count:
            break
    return events


async def _replay(base_url: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(f"{base_url}/replay", params={"delay": 0})


async def test_subscribe_yields_only_matching_tags(base_url):
    task = asyncio.create_task(_collect(base_url, ("press",), 3))
    await _wait_for_subscriber(base_url)
    await _replay(base_url)

    events = await asyncio.wait_for(task, timeout=TIMEOUT)

    assert [e.tag for e in events] == ["press", "press", "press"]
    assert "Day 3" in events[0].text


async def test_no_tags_receives_everything(base_url):
    task = asyncio.create_task(_collect(base_url, (), 5))
    await _wait_for_subscriber(base_url)
    await _replay(base_url)

    events = await asyncio.wait_for(task, timeout=TIMEOUT)

    assert [e.tag for e in events] == [
        "social",
        "press",
        "regulator",
        "press",
        "press",
    ]


async def test_event_is_fully_populated(base_url):
    task = asyncio.create_task(_collect(base_url, ("press",), 1))
    await _wait_for_subscriber(base_url)
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{base_url}/emit", json={"tag": "press", "text": "a briefing"}
        )

    (event,) = await asyncio.wait_for(task, timeout=TIMEOUT)

    assert isinstance(event, Event)
    assert (event.tag, event.text) == ("press", "a briefing")
    assert event.seq > 0 and event.ts > 0


async def test_filtered_subscriber_sees_seq_gaps(base_url):
    """Gaps are expected, not lost events - the client must not try to hide them."""
    task = asyncio.create_task(_collect(base_url, ("press",), 3))
    await _wait_for_subscriber(base_url)
    await _replay(base_url)

    events = await asyncio.wait_for(task, timeout=TIMEOUT)
    seqs = [e.seq for e in events]

    assert seqs == sorted(seqs)
    # The scripted feed puts social/regulator events between the press ones.
    assert seqs[-1] - seqs[0] > len(seqs) - 1


async def test_unreachable_server_raises_when_reconnect_disabled():
    """reconnect_seconds=None must surface the error instead of retrying forever."""
    with pytest.raises(httpx.HTTPError):
        async for _ in subscribe(
            "press", url="http://127.0.0.1:1", reconnect_seconds=None
        ):
            pass

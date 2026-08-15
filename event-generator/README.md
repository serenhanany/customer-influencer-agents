# Event Generator

Fires crisis events into the HappyTuna simulation. Team 3 owns this outright — no other team
controls when events fire (see the repo-root [`PROJECT_README.md`](../PROJECT_README.md) §4).

It runs as its own container and fans events out to subscribers over HTTP, so the agents that
react to a crisis can live in completely separate services.

---

## Architecture

```
                        ┌──────────────────── container ────────────────────┐
                        │                                                   │
  POST /replay ────────►│  event_generator.py                               │
   (scripted feed)      │    CRISIS_FEED  ── 5 briefings, Day 1 → Day 10    │
                        │        │                                          │
                        │        ▼                                          │
  POST /emit ──────────►│  _Sequencer     stamps seq + ts once per event    │
   (one-off injection)  │        │                                          │
                        │        ▼                                          │
                        │  event_broker.py                                  │
                        │    Event        in-process pub/sub, keyed by tag  │
                        │        │                                          │
                        │        ├── listener ──► queue ──┐                 │
                        │        ├── listener ──► queue ──┤                 │
                        │        └── listener ──► queue ──┤                 │
                        │                                 │                 │
                        │  server.py       one SSE stream per queue         │
                        └─────────────────────────────────┼─────────────────┘
                                                          │  GET /subscribe
                                        ┌─────────────────┴─────────────────┐
                                        │  event_client.subscribe(tag)      │
                                        │  timeouts · keepalives · retries  │
                                        └─┬───────────────┬───────────────┬─┘
                                          ▼               ▼               ▼
                                    CEO agent      customer agent   example_subscriber.py
                                    (regulator)    (social)         (press)
```

`event_broker.py` is a plain in-process pub/sub — `subscribe()` holds a Python function and
`emit()` calls it directly. `server.py` wraps it so "register a callback" becomes "hold open a GET
request"; each connected client gets its own queue and its own SSE stream. The broker is untouched
by the HTTP layer and stays usable directly for in-process callers and tests.

### How one event travels

```
  POST /replay
       │
       ▼
  worker thread ──────► Event.emit("press", envelope)
  (generate() sleeps,          │
   so it can't run on          ├──► listener A  ─── call_soon_threadsafe ──┐
   the event loop)             │    (tag=press)                            │
                               │                                           ▼
                               ├──► listener B  ── not subscribed ── skip   event loop
                               │    (tag=social)                            │
                               └──► listener C  ─── call_soon_threadsafe ──┤
                                    (tag=press)                            ▼
                                                                   asyncio.Queue
                                                                           │
                                                                           ▼
                                                              data: {...}\n\n  → client
```

Two details that matter if you change this code:

- **`generate()` is synchronous and sleeps between events**, so `/replay` runs it on a worker
  thread. That means `emit()` fires off-loop while subscriber queues live on the loop — pushes go
  through `loop.call_soon_threadsafe`, never a bare `put_nowait`.
- **`seq` is stamped once per event, not once per subscriber.** Two clients watching the same
  event must see the same `seq`, otherwise the number is useless for spotting a dropped event.

---

## Running it

From the repo root:

```bash
docker compose up --build event-generator
```

The API is then at **`http://localhost:8006`** (port 8000 inside the container).

Without Docker:

```bash
cd event-generator
pip install -r requirements.txt
uvicorn server:app --port 8006
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/subscribe?tag=press` | Open an SSE stream. Repeat `tag` for several; **omit it to receive every tag.** |
| `POST` | `/emit` | Inject one event: `{"tag": "...", "text": "..."}` |
| `POST` | `/replay?delay=2.0` | Play the scripted feed once. `delay` is seconds between events. |
| `GET` | `/tags` | Tags the scripted feed uses |
| `GET` | `/health` | Liveness + current subscriber count |

### Event envelope

Every SSE frame is `data:` followed by one JSON object:

```json
{
  "tag": "press",
  "text": "Day 7 - Nationwide recall underway.\nHappyTuna has issued...",
  "seq": 4,
  "ts": 1786827626.4921272
}
```

`seq` increments once per emitted event across the whole server. A subscriber filtered to one tag
will see **gaps** — that is expected and is how you tell "not for me" from "lost".

The stream also carries `: ping` comment lines every 15s. They keep idle connections from being
closed by intermediaries; ignore any line that doesn't start with `data:`.

### The scripted feed

Five briefings escalating a salmonella outbreak, in `event_generator.py`:

| # | Tag | Event |
|---|---|---|
| 1 | `social` | Day 1 — social listening alert, 14 posts, lot HT-4471-B named |
| 2 | `press` | Day 3 — local news pickup, 12 confirmed illnesses |
| 3 | `regulator` | Day 5 — FDA investigation opened, strain matches patient isolates |
| 4 | `press` | Day 7 — nationwide recall, 1.2M cans, retailers pulling all SKUs |
| 5 | `press` | Day 10 — first fatality, class action, stock down 31% |

---

## Subscribing

### From Python — use `event_client.py`

```python
from event_client import subscribe

async for event in subscribe("press"):
    await my_agent(event.text)
```

That is the whole integration. Pass several tags to follow more than one channel, or none to
receive everything:

```python
async for event in subscribe("press", "regulator"):   # two channels
async for event in subscribe():                        # everything
```

Each `event` is a frozen dataclass with `.tag`, `.text`, `.seq` and `.ts`.

The client is async because the agents are — `ModularAgent.run()` is `async def` and MCP tools are
async, so you can await your model and tool calls straight inside the loop:

```python
async for event in subscribe("regulator"):
    await agent.run(WorldEvent(
        type="regulatory_notice",
        source="event-generator",
        payload={"text": event.text},
    ))
```

**`event_client.py` exists so no agent has to re-solve the transport.** It handles the four things
that silently break a hand-rolled subscriber:

| Handled for you | What goes wrong without it |
|---|---|
| `read=None` on the timeout | Stream dies after a few seconds of quiet — the feed idles by design |
| Skipping `: ping` and blank lines | Crashes on the first keepalive |
| Unwrapping the `data:` JSON envelope | — |
| Reconnect with backoff | Agent silently goes deaf after the first blip |

Two knobs, both optional: `url=` (defaults to `$EVENT_GENERATOR_URL`) and
`reconnect_seconds=None` to fail fast instead of retrying, which is mainly for tests.

`example_subscriber.py` is a working listener built on it — copy it and change two things: the
tag, and the body of `press_agent()`. Run it:

```bash
python example_subscriber.py                       # terminal A
curl -X POST http://localhost:8006/replay          # terminal B
```

Point it elsewhere with `EVENT_GENERATOR_URL` — inside the Docker network that's
`http://event-generator:8000`, not `localhost:8006`.

### From the shell

```bash
curl -N "http://localhost:8006/subscribe?tag=press"              # one tag
curl -N "http://localhost:8006/subscribe?tag=press&tag=social"   # several
curl -N "http://localhost:8006/subscribe"                        # everything
```

### Injecting your own event

```bash
curl -X POST http://localhost:8006/emit \
  -H 'Content-Type: application/json' \
  -d '{"tag":"press","text":"Day 12 - Senate hearing scheduled."}'
```

---

## Backpressure

Each subscriber has a 100-event queue. If a client falls behind, the **oldest** event is dropped,
not the newest — a slow agent should still end up with the current state of the crisis rather than
a stale prefix of it. Drops are counted per connection.

If your handler is slow (an LLM call, say), hand the text to a thread or a queue rather than
blocking the read loop.

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Self-contained — no external network, no API keys, no container.

Both suites work around the same obstacle: httpx's `ASGITransport` awaits the whole ASGI app
before returning a response, so an endless SSE stream never completes and the call just hangs.

- `test_server.py` drives the ASGI protocol directly (`SSEClient`), which also lets a test cancel
  a connection and assert the disconnect cleanup ran. Use it if you add server-side stream tests.
- `test_client.py` can't do that — the client speaks real HTTP — so it runs uvicorn on an
  ephemeral loopback port. No fixed port, so it won't collide with a running container.

---

## Files

| File | |
|---|---|
| `event_broker.py` | `Event` — in-process pub/sub keyed by tag |
| `event_generator.py` | `CRISIS_FEED` + `generate()` — the scripted crisis |
| `server.py` | FastAPI app: SSE fan-out, `/emit`, `/replay` |
| `event_client.py` | `subscribe()` — what agents import to listen |
| `example_subscriber.py` | Working listener; the template to copy |
| `tests/test_server.py` | Server tests, driven through ASGI |
| `tests/test_client.py` | Client tests, against uvicorn on a loopback port |
| `CLAUDE.md` | Coding guidelines for this folder |

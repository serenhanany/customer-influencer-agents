"""Module 3 — world event rendering + inbox injection."""

from modular_agent.events import EventInbox, WorldEvent


def test_event_render_includes_type_and_payload():
    ev = WorldEvent(type="news_article", source="news", payload={"headline": "Recall issued"})
    text = ev.render()
    assert "news_article" in text
    assert "Recall issued" in text
    assert ev.id  # auto-generated


def test_inbox_inject_and_get():
    inbox = EventInbox()
    ev = WorldEvent(type="viral_post")
    inbox.inject(ev)
    assert len(inbox) == 1
    got = inbox.get_nowait()
    assert got.id == ev.id
    assert inbox.empty()


def test_inbox_subscriber_fires():
    inbox = EventInbox()
    seen = []
    inbox.subscribe(lambda e: seen.append(e.type))
    inbox.inject(WorldEvent(type="ceo_statement"))
    assert seen == ["ceo_statement"]

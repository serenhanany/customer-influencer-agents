import re
from datetime import datetime, timezone
from typing import Optional

from models import (
    Ticket,
    TicketCreate,
    TicketPatch,
    ActivityLogEntry,
    TicketStatus,
)

_tickets: dict[str, Ticket] = {}
_activity_log: list[ActivityLogEntry] = []
_ticket_counter: int = 0
_log_counter: int = 0

_ANGRY_WORDS = {
    "dangerous", "disgusting", "furious", "unacceptable", "poison",
    "sick", "ill", "contaminated", "outraged", "horrible", "awful",
}
_FRUSTRATED_WORDS = {
    "frustrating", "frustrated", "annoying", "ridiculous", "irritating",
}
_FRUSTRATED_PHRASES = {"waiting forever", "still not resolved", "still waiting"}
_POSITIVE_WORDS = {"thanks", "great", "love", "appreciate", "happy"}
_POSITIVE_PHRASES = {"thank you"}
_NEGATIONS = {"not", "never", "no", "isnt", "wasnt", "dont", "doesnt", "cant", "wont"}


def _has_unnegated_word(words: set[str], tokens: list[str]) -> bool:
    for i, tok in enumerate(tokens):
        if tok in words:
            window = tokens[max(0, i - 2):i]
            if any(w in _NEGATIONS for w in window):
                continue
            return True
    return False


def score_sentiment(description: str) -> tuple[str, str]:
    text = description.lower().replace("'", "")
    tokens = re.split(r"\W+", text)

    if _has_unnegated_word(_ANGRY_WORDS, tokens):
        return "angry", "keyword_v1"
    if _has_unnegated_word(_FRUSTRATED_WORDS, tokens) or any(
        p in text for p in _FRUSTRATED_PHRASES
    ):
        return "frustrated", "keyword_v1"
    if _has_unnegated_word(_POSITIVE_WORDS, tokens) or any(
        p in text for p in _POSITIVE_PHRASES
    ):
        return "positive", "keyword_v1"
    return "neutral", "keyword_v1"


_LOGGABLE_FIELDS = {
    "status": "status_changed",
    "priority": "priority_changed",
    "sentiment": "sentiment_scored",
    "assignee": "assigned",
    "reply_message": "replied",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_ticket_id() -> str:
    global _ticket_counter
    _ticket_counter += 1
    return f"TCK-{_ticket_counter:05d}"


def _next_log_id() -> str:
    global _log_counter
    _log_counter += 1
    return f"LOG-{_log_counter:06d}"


def _build_details(
    field: str, old_value, new_value, patch_data: dict, ticket: Ticket
) -> dict:
    if field == "status":
        return {"from": old_value, "to": new_value}
    if field == "priority":
        return {"from": old_value, "to": new_value}
    if field == "sentiment":
        method = patch_data.get("sentiment_method") or ticket.sentiment_method
        return {"sentiment": new_value, "method": method}
    if field == "assignee":
        return {"assignee": new_value}
    if field == "reply_message":
        return {"message": new_value}
    return {}


def _write_log(
    entity_id: str,
    activity_type: str,
    actor: str,
    details: dict,
) -> ActivityLogEntry:
    entry = ActivityLogEntry(
        log_id=_next_log_id(),
        entity_type="ticket",
        entity_id=entity_id,
        activity_type=activity_type,
        timestamp=_now(),
        actor=actor,
        details=details,
        schema_version=1,
    )
    _activity_log.append(entry)
    return entry


def create_ticket(data: TicketCreate) -> Ticket:
    ticket_id = _next_ticket_id()
    now = _now()
    sentiment_value, sentiment_method = score_sentiment(data.description)
    ticket = Ticket(
        ticket_id=ticket_id,
        customer_id=data.customer_id,
        created_at=now,
        updated_at=now,
        status=TicketStatus.open,
        priority=data.priority,
        issue_type=data.issue_type,
        subject=data.subject,
        description=data.description,
        linked_product_batch=data.linked_product_batch,
        sentiment=sentiment_value,
        sentiment_method=sentiment_method,
        schema_version=1,
    )
    _tickets[ticket_id] = ticket
    _write_log(ticket_id, "created", "system", {})
    _write_log(ticket_id, "sentiment_scored", "system", {
        "sentiment": sentiment_value,
        "method": sentiment_method,
    })
    return ticket


def get_ticket(ticket_id: str) -> Optional[Ticket]:
    return _tickets.get(ticket_id)


def list_tickets(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    issue_type: Optional[str] = None,
    linked_product_batch: Optional[str] = None,
) -> list[Ticket]:
    results: list[Ticket] = list(_tickets.values())
    if customer_id is not None:
        results = [t for t in results if t.customer_id == customer_id]
    if status is not None:
        results = [t for t in results if t.status == status]
    if issue_type is not None:
        results = [t for t in results if t.issue_type == issue_type]
    if linked_product_batch is not None:
        results = [t for t in results if t.linked_product_batch == linked_product_batch]
    return results


def patch_ticket(ticket_id: str, patch: TicketPatch) -> Optional[Ticket]:
    ticket = _tickets.get(ticket_id)
    if ticket is None:
        return None

    patch_data: dict = patch.model_dump(exclude_unset=True)
    actor: str = patch_data.pop("actor", None) or "system"

    any_changed = False
    for field, new_value in patch_data.items():
        old_value = getattr(ticket, field)
        if old_value == new_value:
            continue
        any_changed = True
        if field in _LOGGABLE_FIELDS:
            details = _build_details(field, old_value, new_value, patch_data, ticket)
            _write_log(ticket_id, _LOGGABLE_FIELDS[field], actor, details)
        elif field == "sentiment_method":
            sentiment_also_changing = (
                "sentiment" in patch_data
                and patch_data["sentiment"] != ticket.sentiment
            )
            if not sentiment_also_changing:
                _write_log(
                    ticket_id,
                    "sentiment_scored",
                    actor,
                    {"sentiment": ticket.sentiment, "method": new_value},
                )

    if not any_changed:
        return ticket

    ticket_dict = ticket.model_dump()
    ticket_dict.update(patch_data)
    ticket_dict["updated_at"] = _now()
    updated = Ticket(**ticket_dict)
    _tickets[ticket_id] = updated
    return updated


def get_activity_log(ticket_id: str) -> list[ActivityLogEntry]:
    entries = [e for e in _activity_log if e.entity_id == ticket_id]
    return sorted(entries, key=lambda e: e.timestamp)
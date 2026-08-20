"""Seeds real safety_concern tickets for the Day 1 salmonella crisis-feed
scenario (ceo_agent/main.py's CRISIS_FEED, sourced from
event-generator/event_generator.py).

Day 1's briefing describes unconfirmed social-media chatter about lot
HT-4471-B. This script puts matching tickets into the live Customer Support
queue so a CEO that actually checks the support system -- instead of taking
the rumor on faith -- finds real corroborating complaints.

These are seeded here, externally, rather than via the CEO's own
support.create_ticket tool, because that tool is deliberately denied to the
CEO role in roles.yaml: filing its own ticket would let the CEO manufacture
the evidence it's being evaluated on. Seeding scenario ground truth is the
simulation operator's job, the same role the event-generator or a live
customer agent would play.

Run with:  python seed_salmonella_tickets.py
Requires the customer-support-api service reachable (default
http://localhost:8013; override with CS_API_URL).
"""
import json
import os
import urllib.request

API_URL = os.environ.get("CS_API_URL", "http://localhost:8013")
LOT = "HT-4471-B"

TICKETS = [
    {
        "customer_id": "CUST-2001",
        "issue_type": "safety_concern",
        "subject": "Got extremely sick after HappyTuna tuna",
        "description": (
            "I ate a can of HappyTuna Classic Chunk Light Tuna last night and "
            "started throwing up with a fever a few hours later. The can was "
            "from lot HT-4471-B. This is scary, please investigate."
        ),
        "linked_product_batch": LOT,
        "priority": "high",
    },
    {
        "customer_id": "CUST-2002",
        "issue_type": "safety_concern",
        "subject": "Whole family sick - possible food poisoning",
        "description": (
            "My husband and I both got severe stomach cramps and diarrhea "
            "after eating your tuna. Checked the can and it's marked "
            "HT-4471-B. We are considering going to the ER."
        ),
        "linked_product_batch": LOT,
        "priority": "critical",
    },
    {
        "customer_id": "CUST-2003",
        "issue_type": "safety_concern",
        "subject": "Nausea and fever after eating canned tuna",
        "description": (
            "Felt nauseous and feverish about 8 hours after eating HappyTuna "
            "tuna from lot HT-4471-B. Saw other people online reporting the "
            "same thing."
        ),
        "linked_product_batch": LOT,
        "priority": "high",
    },
    {
        "customer_id": "CUST-2004",
        "issue_type": "safety_concern",
        "subject": "Is there a recall on lot HT-4471-B?",
        "description": (
            "Read online that people are getting sick from lot HT-4471-B. I "
            "ate a can from that lot two days ago and now have stomach pain "
            "and chills. Please advise."
        ),
        "linked_product_batch": LOT,
        "priority": "medium",
    },
]


def _get(path: str) -> object:
    with urllib.request.urlopen(f"{API_URL}{path}") as resp:
        return json.load(resp)


def _post(path: str, body: dict) -> object:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def main() -> None:
    existing = _get(f"/tickets?linked_product_batch={LOT}&issue_type=safety_concern")
    if existing:
        print(f"{len(existing)} safety_concern ticket(s) already exist for lot {LOT}; skipping seed.")
        for t in existing:
            print(f"  {t['ticket_id']}: {t['subject']}")
        return

    print(f"Seeding {len(TICKETS)} safety_concern ticket(s) for lot {LOT}...")
    for ticket in TICKETS:
        created = _post("/tickets", ticket)
        print(f"  Created {created['ticket_id']}: {created['subject']} (sentiment={created['sentiment']})")


if __name__ == "__main__":
    main()

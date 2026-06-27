# Customer Support API

FastAPI service for the HappyTuna crisis-simulation project (Team 3).

## Running the server

```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

Interactive docs are at `http://localhost:8000/docs`.

---

## Example requests

### 1. Create a ticket

```bash
curl -s -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-1190",
    "issue_type": "safety_concern",
    "subject": "Metal fragment in canned tuna",
    "description": "Found a sharp piece of metal in batch #4471.",
    "linked_product_batch": "4471",
    "priority": "high"
  }' | python -m json.tool
```

Example response:

```json
{
  "ticket_id": "TCK-00001",
  "customer_id": "CUST-1190",
  "created_at": "2026-06-27T10:00:00.000000+00:00",
  "updated_at": "2026-06-27T10:00:00.000000+00:00",
  "status": "open",
  "priority": "high",
  "issue_type": "safety_concern",
  "subject": "Metal fragment in canned tuna",
  "description": "Found a sharp piece of metal in batch #4471.",
  "linked_product_batch": "4471",
  "sentiment": null,
  "sentiment_method": null,
  "assignee": null,
  "reply_message": null,
  "schema_version": 1
}
```

---

### 2. Patch the ticket's status (and set the actor)

```bash
curl -s -X PATCH http://localhost:8000/tickets/TCK-00001 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "actor": "COO-1"
  }' | python -m json.tool
```

The server diffs old vs. new values automatically and writes a `status_changed`
activity-log entry. The caller never touches the log directly.

---

### 3. Fetch the activity log — confirm the auto-log entry appeared

```bash
curl -s http://localhost:8000/tickets/TCK-00001/activity | python -m json.tool
```

Example response (two entries: creation + status change):

```json
[
  {
    "log_id": "LOG-000001",
    "entity_type": "ticket",
    "entity_id": "TCK-00001",
    "activity_type": "created",
    "timestamp": "2026-06-27T10:00:00.000000+00:00",
    "actor": "system",
    "details": {},
    "schema_version": 1
  },
  {
    "log_id": "LOG-000002",
    "entity_type": "ticket",
    "entity_id": "TCK-00001",
    "activity_type": "status_changed",
    "timestamp": "2026-06-27T10:01:00.000000+00:00",
    "actor": "COO-1",
    "details": {
      "from": "open",
      "to": "in_progress"
    },
    "schema_version": 1
  }
]
```

---

### 4. Filter tickets by issue_type=safety_concern

```bash
curl -s "http://localhost:8000/tickets?issue_type=safety_concern" | python -m json.tool
```

Combine filters freely — all query params are optional:

```bash
# Safety tickets that are still open, for a specific batch
curl -s "http://localhost:8000/tickets?issue_type=safety_concern&status=open&linked_product_batch=4471"
```

---

## Auto-logging rules

`PATCH /tickets/{ticket_id}` diffs old vs. new for each field and writes one
log entry per changed field:

| Changed field   | `activity_type`   | `details` shape                                      |
|-----------------|-------------------|------------------------------------------------------|
| `status`        | `status_changed`  | `{"from": "open", "to": "in_progress"}`              |
| `priority`      | `priority_changed`| `{"from": "medium", "to": "critical"}`               |
| `sentiment`     | `sentiment_scored`| `{"sentiment": "angry", "method": "keyword_v1"}`     |
| `assignee`      | `assigned`        | `{"assignee": "COO-1"}`                              |
| `reply_message` | `replied`         | `{"message": "We are investigating your complaint."}`|

Pass `"actor"` in the PATCH body to attribute the change (defaults to
`"system"` when omitted). `sentiment_method` can be patched alongside
`sentiment`; it is included in the `sentiment_scored` log details but does
not generate its own log entry.

## Enum values

| Field         | Accepted values                                            |
|---------------|------------------------------------------------------------|
| `status`      | `open`, `in_progress`, `escalated`, `resolved`, `closed`  |
| `priority`    | `low`, `medium`, `high`, `critical`                        |
| `issue_type`  | `quality`, `delivery`, `billing`, `general`, `safety_concern` |
| `sentiment`   | `angry`, `frustrated`, `neutral`, `positive`               |

Invalid values return `422 Unprocessable Entity` automatically.

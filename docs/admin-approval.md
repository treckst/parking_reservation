# Reservation approval API

The main LangGraph mounts three compiled subgraphs: `policy`, `reservation`, and
`admin`. The administrator surface is API-only in the existing trusted local demo.

```text
prepare → check_language → guard_input → classify
          │                              ├─ policy
          │                              └─ reservation [extract → persist_pending → summarize]
          │                                 → admin [await_review interrupt → structured LLM review → ToolNode]
          │                                 → customer reply based on admin_result
          └─ non-English → English rephrase request → END
```

Only English customer requests pass `check_language`. Its structured LLM decision
routes non-English or unclear input to a fixed English reply and ends the turn
before classification or booking writes. Reservation summaries use English.

The customer asks to book through `POST /api/chat`. A complete request needs the
spot ID, same-day start/end ISO timestamps with offsets, name, surname and vehicle
plate. Missing details produce a follow-up question. The new reservation subgraph
extracts details over customer turns. Once complete, it validates the interval
against the fixture slot and opening hours and writes a `pending` row in SQLite.
It then summarizes the saved intent, stores that summary on the same row, and
passes `reservation_id`, `booking_draft` and `reservation_summary` to the compiled
admin subgraph. The unique database ID is named `reservation_id` throughout.
Incomplete or invalid requests never reach summarization or admin review.
The availability snapshot flag is not used for interval decisions.

The additive `booking_requests` table shares the existing booking database with
`transport_slots` and legacy `reservations`. Legacy tables/records are preserved.
Both legacy blocking statuses and new pending/approved rows block overlapping
intervals. `BEGIN IMMEDIATE` serializes the overlap check and insertion. Adjacent
intervals are allowed. Replays use a stable ID derived from thread and request.

Use `GET /api/admin/reservations` to list pending requests and intent summaries.
Each item supplies its `reservation_id`. Resume with:

```http
POST /api/admin/reservations/{reservation_id}/review
Content-Type: application/json

{"response":"approve"}
```

The response text can express approval or rejection. The API verifies the matching
checkpoint is waiting at `admin`, durably claims the review, and submits
`command={"resume": {...}}` to the Agent Server on the original thread. The admin
subgraph has its own LLM node with strict structured output:
`{"response":"approve" | "reject"}`. Its prompt requires explicit unconditional
administrator approval and treats uncertain responses as rejection. Customer text
and reservation summaries cannot supply administrator authorization.

The admin LLM's structured decision is adapted to a fixed tool call executed by
the subgraph's `ToolNode`. The tool receives the reservation ID from injected
state rather than model-generated arguments. Inside `BEGIN IMMEDIATE`, approval
rechecks opening hours and overlaps, excluding its own pending hold, then updates
that same row to `approved`. A rejection or failed rule check sets `rejected` and
releases the hold. This uses a primary-key update (the update side of an upsert):
an absent pending record fails rather than inserting an unvalidated reservation.
Identical finalization retries reuse the durable result; opposite decisions fail.
Existing application `confirmed` rows migrate to `approved` transactionally,
preserving IDs, drafts, summaries and dispatch claims. Legacy fixture statuses
remain unchanged.

Only after the database write succeeds does the admin subgraph return
`admin_result = {"reservation_id": ..., "status": "approved" | "rejected", "reason": ...}`.
The main graph checks that result's ID and status to produce the customer reply.
It has no mock continuation or reservation status write nodes.

Repeated identical reviews reuse the original dispatch; conflicting text returns
409. A lost acknowledgement is reconciled by `admin_review_id` metadata without
creating another resume. If no accepted run can be found, the review remains
`creating` and needs operator investigation; absence of a match does not prove
nonacceptance. An LLM/provider error after resume is a run failure, not an approval.

Customer polling stays `pending` during approval and follows the continuation run
after review. Customer replies use the existing DTO and never expose the booking
draft, admin response, raw checkpoint, or evidence. Conversation history is keyed
by message IDs; query/evidence channels retain their existing collision-checking
reducers. Shared state keys use identical names and types across the graph
schemas, allowing direct `add_node("admin", admin_graph.compile())` composition.
Reservation and admin output schemas restrict updates to their owned keys so
they cannot replace parent history, queries or evidence. `admin_messages`,
`admin_response` and `admin_decision` are private to the admin subgraph;
`admin_result` is its sole output to the parent and is cleared at each new turn.

`BOOKING_DB_PATH` selects the fixture database. It must already exist. Compose
mounts `ingested_mock_data` at `/fixtures` in both graph and API containers, so
pending rows and review dispatch claims survive service restarts and are shared.
Checkpoint and application-registry files remain separate. Rebuild the graph
image first, then the API image, and start Compose to use the new code; no live
model calls or deployment are needed for the mocked offline tests.

Implementation follows LangGraph's [compiled subgraph pattern](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
and [interrupt/resume pattern](https://docs.langchain.com/oss/python/langgraph/interrupts).

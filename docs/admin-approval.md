# Reservation approval API

The main LangGraph mounts three compiled subgraphs: `policy`, `reservation`, and
`admin`. The administrator surface is API-only in the existing trusted local demo.

```text
prepare → classify → policy
                   → reservation [extract → summarize → persist_pending]
                     → admin [await_review interrupt → structured LLM review]
                       → approve → mock_node → customer reply
                       → reject  → reject    → customer reply
```

The customer asks to book through `POST /api/chat`. A complete request needs the
spot ID, same-day start/end ISO timestamps with offsets, name, surname and vehicle
plate. Missing details produce a follow-up question. The new reservation subgraph
extracts details and summarizes the intent. It validates the interval against the
fixture slot and opening hours, then writes a `pending` row in SQLite **before**
interrupting. The availability snapshot flag is not used for interval decisions.

The additive `booking_requests` table shares the existing booking database with
`transport_slots` and legacy `reservations`. Legacy tables/records are preserved.
Both legacy blocking statuses and new pending/confirmed rows block overlapping
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

The parent conditional edge reads `admin_decision.response`. Only `approve`
reaches `mock_node`, which confirms the pending hold and represents the placeholder
for future downstream work. Rejection releases the hold by marking it rejected.
This is a demo workflow, with no external action executed by the mock node.

Repeated identical reviews reuse the original dispatch; conflicting text returns
409. A lost acknowledgement is reconciled by `admin_review_id` metadata without
creating another resume. If no accepted run can be found, the review remains
`creating` and needs operator investigation; absence of a match does not prove
nonacceptance. An LLM/provider error after resume is a run failure, not an approval.

Customer polling stays `pending` during approval and follows the continuation run
after review. Customer replies use the existing DTO and never expose the booking
draft, admin response, raw checkpoint, or evidence. Conversation history is keyed
by message IDs; query/evidence channels retain their existing collision-checking
reducers. Reservation and admin subgraphs restrict output to their owned keys so
they cannot replace parent history, queries or evidence.

`BOOKING_DB_PATH` selects the fixture database. It must already exist. Compose
mounts `ingested_mock_data` at `/fixtures` in both graph and API containers, so
pending rows and review dispatch claims survive service restarts and are shared.
Checkpoint and application-registry files remain separate. Rebuild the graph
image first, then the API image, and start Compose to use the new code; no live
model calls or deployment are needed for the mocked offline tests.

Implementation follows LangGraph's [compiled subgraph pattern](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
and [interrupt/resume pattern](https://docs.langchain.com/oss/python/langgraph/interrupts).

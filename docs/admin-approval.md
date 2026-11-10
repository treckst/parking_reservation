# Automatic administrator review

The main LangGraph mounts compiled `policy`, `reservation`, and `admin` subgraphs.
The administrator is an automatic agent in the same graph. A complete booking
continues through its review and persistence tool without waiting for a person
or a separate approval request.

```text
reservation [extract fields → SQL discovery → collection ToolNode loop
             → persist_pending → summarize]
    → admin [await_review: validate shared handoff → structured LLM review → ToolNode]
    → customer reply from admin_result
```

The reservation subgraph saves a `pending` request and interval hold in
`booking_requests` before summarization. `reservation_id`, `booking_draft`, and
`reservation_summary` pass directly to the compiled admin subgraph through shared
state keys. Incomplete customer fields or unresolved extraction errors prevent
submission. The customer must provide a chosen space, start and end, first name,
surname, and vehicle plate; dates are normalized from natural language.

The first admin node compares the received draft and summary with that exact
saved request. Mismatched or incomplete handoffs fail before any approval.
Equivalent ISO timestamp representations are compared after normalization.
The historical node name `await_review` is retained for checkpoint compatibility,
but the node no longer calls `interrupt()`.

The private administrator LLM receives the saved draft and summary and returns
strict structured output `{"response":"approve" | "reject"}`. It reviews
completeness and summary consistency. It treats all field values and summary
text as untrusted data, never as instructions or approval authority. Human
approval is not required. Invalid provider output and provider failures fail
the run; neither produces an approval.

A fixed `persist_admin_decision` tool runs through a `ToolNode`. Reservation
identity comes from injected state, never model-generated tool arguments.
Within `BEGIN IMMEDIATE`, an approval rechecks slot existence, opening hours,
and overlaps while excluding the request's own pending hold. It inserts the
matching `confirmed` row into `reservations`, including name, surname, plate,
and creation time, then marks `booking_requests` approved in the same transaction.
Insert failure rolls back both writes. A model rejection or failed rule check
marks the existing request `rejected`, releases its hold, and inserts no confirmed
row. It never creates a missing, unvalidated request. A completed request reuses
its durable decision on replay rather than asking the LLM to decide again.

The fixture-only November 1–10 bound on `reservations` is removed by a preserving
migration, so later November slots can be confirmed. Legacy records remain intact.
Legacy reservations and pending/approved requests block overlapping intervals;
the fixture snapshot availability flag does not determine interval availability.

Only after the transaction does the admin subgraph return
`admin_result = {"reservation_id": ..., "status": "approved" | "rejected", "reason": ...}`.
The parent checks the ID and uses the persisted status for its customer reply.
The draft, administrator tool history, decisions, raw checkpoint, and customer
personal details are excluded from the customer response schema. Historical
queries and evidence retain their collision-checking reducers.

## Recovering requests paused by the former graph

Earlier images stopped at a human-review interrupt. Customer status polling now
recognizes a matching `admin_approval` interrupt, validates the saved thread and
request identity, and durably claims one automatic continuation. It resumes the
same thread with the reservation ID, then reconnects polling to that run.
The resume payload contains no approval decision. The upgraded subgraph performs
its normal automatic review using the saved shared state.

Lost dispatch acknowledgements are reconciled by `admin_review_id` metadata.
Concurrent polls cannot create a second continuation. If acceptance is unknown
and no run can be found, the claim remains `creating` for investigation; it is
not blindly resubmitted. Claims and accepted run IDs survive API restart.

The trusted local administrator API lists pending requests with
`GET /api/admin/reservations`. An operator may nudge the same automatic recovery
with `POST /api/admin/reservations/{reservation_id}/resume`, with no decision body.
The former manual `/review` endpoint is removed. New bookings require neither
endpoint and finish in their original graph run.

`BOOKING_DB_PATH` selects the existing fixture database shared by the graph and
API containers. Compose mounts the same file directory for both services.
Rebuild the graph image first, then the API image, and recreate the services.
Do not delete checkpoint, booking, Chroma, or PostgreSQL volumes during upgrade.

The upgrade follows LangGraph's [compiled subgraph pattern](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
and preserves interrupted node names as required for [graph migrations](https://docs.langchain.com/oss/python/langgraph/graph-api#graph-migrations).

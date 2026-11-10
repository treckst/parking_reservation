# Automatic admin agent

The admin is a compiled subgraph inside the parent parking graph. The REST API
serves the UI and invokes the parent graph through the SDK. It does not approve,
reject or resume admin decisions.

```text
reservation [extract -> SQL discovery -> collect -> persist_pending -> summarize]
    -> admin [validate_request -> structured LLM review -> ToolNode]
    -> customer reply from admin_result
```

The reservation subgraph writes a pending hold to `booking_requests` after all
required customer fields have been saved and validated. It passes `reservation_id`,
`booking_draft` and `reservation_summary` directly to the admin through shared
state keys. Names, surname, vehicle plate, spot and normalized visit times are
required; the application creates IDs and status metadata.

The admin first compares the shared draft and summary with the exact saved
request. Its private LLM reviews completeness and summary consistency, returning
strict structured output `{"response":"approve" | "reject"}`. Customer values and
summary text are untrusted data and cannot authorize tool behavior. Invalid model
output or a provider failure fails the run and cannot approve the request.

A fixed `persist_admin_decision` ToolNode uses the reservation ID from injected
state. Approval rechecks slot existence, opening hours and overlaps under
`BEGIN IMMEDIATE`, excluding the request's own pending hold. It inserts a
`confirmed` row in `reservations` and marks the request `approved` in one
transaction. Insert failure rolls back both writes. Rejection updates the
existing request to `rejected`, releases its hold and inserts no confirmed row.
Replays return the durable result without another decision or duplicate insert.

Only after persistence does the subgraph return `admin_result` to the parent.
The parent checks the reservation ID and produces the customer reply from that
result. Admin tool history, private draft fields and raw checkpoints stay outside
the customer response schema. The fixture-only November 1-10 reservation date
constraint is removed by a preserving migration, enabling later November dates.

There are no admin HTTP endpoints, approval interrupts, resume dispatch claims,
or separate admin services. Booking writes remain in the graph; ordinary REST
chat and conversation routes continue to support the UI. The graph and API images
must be rebuilt and recreated to deploy source changes. Booking, checkpoint,
Chroma and PostgreSQL data use their existing persistent storage.

# Requirements: Parking Reservation Assistant

**Defined:** 2026-11-10
**Review status:** Approved; all 49 v1 requirements and Vertical MVP delivery were confirmed by the user on 2026-11-10.
**Core Value:** Customers can request a valid parking reservation through conversation, with accurate availability, no overlapping bookings, administrator approval, and no disclosure of other customers' personal details.

## v1 Requirements

### Graph and Conversation State

- [ ] **GRAPH-01**: The application uses `gpt-6-luna` through LangChain and LangGraph as its only agent frameworks; unavailable model access produces an explicit configuration error rather than a silent model substitution.
- [ ] **GRAPH-02**: Graph input, output, main state, intent classification, evidence assessment, and booking details have explicit typed schemas validated at their boundaries.
- [ ] **GRAPH-03**: Customers can continue a conversation using its `thread_id`, retaining messages and booking details across turns and deployed graph-server restarts.
- [ ] **GRAPH-04**: Each new question has a distinct query index, and its retrieved documents and SQL results remain in thread state after subsequent questions.
- [ ] **GRAPH-05**: A custom main-state reducer merges SQL and vector evidence for the same query without clearing earlier queries, overwriting parallel results, or duplicating retried evidence updates.
- [ ] **GRAPH-06**: Concurrent submissions to the same thread are serialized or explicitly rejected so they cannot mix query indices, booking details, or replies.

### Hybrid Retrieval and Grounded Answers

- [ ] **RAG-01**: A router returns structured intent for policy lookup, live availability/pricing, or reservation management, including a `check_availability` decision that controls conditional graph routing.
- [ ] **RAG-02**: Policy/general questions execute a dedicated Chroma retrieval node without running an unrelated SQL availability branch.
- [ ] **RAG-03**: Availability questions execute dedicated vector and SQL retrieval nodes in parallel and assess their results after the required branches finish.
- [ ] **RAG-04**: Availability and PLN/hour prices come from current SQL records for the requested period and slot criteria; neither policy prose, the seed snapshot flag, nor prior-query evidence overrides those facts.
- [ ] **RAG-05**: An LLM judge returns structured evidence sufficiency, and conditional edges return a clear no-available-information response when the retrieved documents and records cannot support an answer.
- [ ] **RAG-06**: Customers receive distinct outcomes for insufficient evidence, a successful search with no free slots, invalid criteria, and a dependency failure; failed retrieval is not presented as an empty successful result.
- [ ] **RAG-07**: Policy queries use embeddings compatible with the stored collection, retain source/page identities, and retrieve evidence only within its supported scope; the existing collection remains intact while compatibility is established.

### Booking Collection, Validation, and Approval

- [ ] **BOOK-01**: The assistant collects Name, Surname, Car Number, Zone/Slot, and Reservation Period across turns, requesting missing information while retaining valid details already supplied.
- [ ] **BOOK-02**: Customers can correct collected details; changes to the slot or period invalidate previous availability checks and trigger fresh validation.
- [ ] **BOOK-03**: Unsupported or malformed license plates receive a useful validation message before a booking is written.
- [ ] **BOOK-04**: Reservation periods are validated against start/end ordering, Europe/Warsaw time semantics, facility working hours, slot/type identity, and existing daily inventory; unsupported dates are reported explicitly.
- [ ] **BOOK-05**: `check_availability(start_time, end_time, spot_type)` returns matching free slots using current reservation overlaps, including pending holds, rather than the fixture's snapshot availability flag.
- [ ] **BOOK-06**: `create_reservation(name, surname, car_number, slot_id, start_time, end_time)` atomically rechecks conflicts and commits a `PENDING` hold; concurrent overlapping requests cannot both acquire the same interval.
- [ ] **BOOK-07**: A committed pending booking holds its interval until an administrator decision or authorized cancellation; the assistant reports pending success only after the transaction commits.
- [ ] **BOOK-08**: Retrying the same booking operation after a graph retry or lost response returns its persisted result without creating a duplicate reservation.
- [ ] **BOOK-09**: `cancel_reservation(reservation_id, car_number)` validates the caller's allowed booking scope and plate before cancelling and releasing the hold, without revealing unrelated booking details.
- [ ] **BOOK-10**: Administrators can confirm a pending booking or reject it as `CANCELLED`; invalid or racing status transitions cannot resurrect a cancelled booking, and later customer responses reflect the persisted SQL status.

### Privacy and Guardrails

- [ ] **PRIV-01**: Input guardrails block prompt-injection attempts that request hidden instructions, unrelated personal records, or unauthorized tool behavior.
- [ ] **PRIV-02**: User messages and retrieved text cannot grant SQL privileges or bypass deterministic booking validation; database tools expose bounded operations using parameterized ORM queries.
- [ ] **PRIV-03**: Customer SQL results and API projections exclude other customers' names, license plates, bookings, and internal graph state, including in error responses.
- [ ] **PRIV-04**: Customer thread and booking access is bound to a server-validated browser session; supplying another session's thread ID, reservation ID, or plate alone does not grant access.
- [ ] **PRIV-05**: A final output guardrail node blocks or scrubs unauthorized sensitive information before an assistant reply reaches the customer.
- [ ] **PRIV-06**: Customers and administrators use separate routes and UI surfaces without login or application API keys within a trusted local deployment; internal graph services are not exposed as a customer-access bypass.

### REST API and Simple Frontend

- [ ] **API-01**: `POST /api/chat` accepts a message and `thread_id`, invokes the deployed Agent Server through `langgraph_sdk`, and returns the assistant reply plus a safe updated reservation-state projection.
- [ ] **API-02**: `GET /api/slots` returns inventory and SQL-derived availability for an explicit selected date/period without disclosing reservation PII.
- [ ] **API-03**: The administrator's `GET /api/reservations` lists reservation records for the bookings panel.
- [ ] **API-04**: The administrator's `PATCH /api/reservations/{id}` accepts `CONFIRMED` or `CANCELLED` and applies the shared booking transition rules.
- [ ] **API-05**: FastAPI enforces Pydantic request/response schemas, appropriate HTTP status codes, and explicitly configured CORS.
- [ ] **UI-01**: Customers can ask questions and request bookings through a simple conversational panel with quick-action prompts and clear validation, pending, and failure feedback.
- [ ] **UI-02**: A simple slot grid displays its selected period and SQL-derived Available, Occupied, or Pending status, with EV capability visible independently of availability status.
- [ ] **UI-03**: The slot grid automatically refreshes after committed chatbot booking/cancellation transactions and administrator decisions, including changes made from a separate local tab.
- [ ] **UI-04**: A separate administrator panel displays SQL reservation records and lets the administrator approve or reject pending requests with visible results.

### Delivery, Readability, and Verification

- [ ] **DEL-01**: A repeatable migration preserves existing SQLite records and daily slot identities while supporting `PENDING` and valid new bookings on existing November 11–30 inventory dates.
- [ ] **DEL-02**: The graph is packaged and started as an Agent Server image using deployment JSON and declared dependencies before the FastAPI SDK integration is accepted.
- [ ] **DEL-03**: Docker Compose runs the graph server, PostgreSQL, Redis, Chroma, and application API/frontend with persistent storage; graph tools and administrator routes share the same operational SQLite database and booking rules.
- [ ] **DEL-04**: Graph startup waits for Chroma, PostgreSQL, and Redis readiness, and service addresses work from inside the deployed containers.
- [ ] **DEL-05**: Setup documentation provides reproducible dependency installation, configuration, image builds, startup, and verification steps, including clear model/embedding/server prerequisite failures without committing credentials.
- [ ] **DEL-06**: Application code uses clear names, small functions, explicit schemas, and simple module boundaries; comments explain constraints or decisions without unnecessary abstraction or excessive narration.
- [ ] **TEST-01**: Pytest unit and integration tests verify interval overlap detection, boundary validation, concurrent pending holds, retry deduplication, and approval/cancellation transitions using isolated test databases.
- [ ] **TEST-02**: Pytest REST tests verify the specified endpoints, schemas, status codes, privacy boundaries, and the deployed SDK-backed chat path.
- [ ] **TEST-03**: Reviewed RAG cases verify expected source/page retrieval against real Chroma, structured routing/judging, supported answers, unsupported-question abstention, and dependency-failure behavior.
- [ ] **TEST-04**: Graph tests verify multi-turn field collection, corrections, persistent thread continuity, reducer merge/history behavior, same-thread contention, injection handling, and cross-session isolation.
- [ ] **TEST-05**: An integrated local walkthrough verifies chat, the grid, administrator decisions, and shared booking state against the deployed services; deterministic tests and configured live-model checks are reported separately, with skipped live checks identified as unverified.

## v2 Requirements

No additional release scope is committed. Features outside v1 require a separate scope decision rather than an implied future promise.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Customer/admin accounts, login, and application API-key authentication | Explicitly excluded for this local trusted demo. Provider and deployment credentials remain server configuration. |
| Public production exposure | Separate routes do not establish administrator authorization or customer identity. |
| Payments, deposits, payment providers, and automatic refunds | The approved scope covers hourly pricing and reservation management. |
| Additional agent frameworks or arbitrary model-generated SQL execution | The approved stack is LangChain/LangGraph with bounded SQL tools. |
| Automatic pending expiry, waitlists, and proactive notifications | No expiry or queue policy was requested; holds persist until a decision or cancellation. |
| Replacing operational SQLite with PostgreSQL or distributing SQLite across hosts | SQLite is the requested booking source; PostgreSQL serves graph infrastructure. |
| Cross-thread user profiles or long-term personalization | Only short-term conversation memory is required. |
| Physical occupancy sensors, charging management, and navigation maps | The fixtures describe scheduled bookings and slot attributes, not those systems. |
| Rich dashboards, a complex design system, and native mobile clients | The frontend must remain very simple. |
| Fabricated inventory or extrapolated policy validity beyond supplied coverage | Missing data must be reported rather than invented. |

## Planning Decisions

These refine accepted requirements; they do not add release features or silently choose product policy. Resolve them before implementing the affected phase and record the result in project/phase context.

| Decision | Relevant Requirements | Current Boundary |
|----------|-----------------------|------------------|
| Interval endpoints, same-day scope, legacy blocking statuses, and past-time/demo-clock behavior | BOOK-04–07, UI-02, DEL-01 | Existing data uses same-day November periods; adjacent interval behavior and legacy mappings need an explicit consistent rule. |
| Supported plate formats, normalization, type matching, and zone-only slot selection | BOOK-01–06 | Validate supported formats and existing inventory; ask when details are ambiguous. |
| Grid default date/period, Occupied semantics, status priority, and refresh latency | API-02, UI-02–03 | Always show the selected interval; EV remains a separate attribute. |
| Browser-session lifetime, new-chat behavior, and cancellation of ownerless seeded bookings | GRAPH-03, BOOK-09, PRIV-04 | A thread/reservation ID or plate alone does not authorize access. No account system is planned. |
| Query/retry identity, per-thread contention policy, and partial retrieval failures | GRAPH-04–06, RAG-03–06, BOOK-08 | Preserve earlier evidence, prevent duplicate writes, and distinguish unavailable services from insufficient information. |
| Admin status reconciliation and repeat/conflict responses | BOOK-10, API-04, UI-03 | SQL is authoritative; do not require an indefinite graph interrupt merely because a booking is pending. |
| Model account access, embedding provenance, resolved dependencies, and Agent Server entitlement | GRAPH-01, RAG-07, DEL-02–05 | Verify through early setup checks; do not silently substitute models, embedding spaces, or deployment architecture. |

## Acceptance Criteria

- A customer asks a supported policy question and receives an evidence-backed answer; an unsupported question receives the explicit no-information response.
- Availability answers and the grid agree for the same selected period; retained evidence from an earlier question cannot override newer SQL facts.
- A customer supplies booking details over several turns, corrects a detail, and creates one pending hold without duplicating a write on retry.
- Competing sessions cannot acquire overlapping holds. Approval retains the blocked interval; rejection/cancellation releases it and refreshes the UI.
- Customer responses never disclose another session's booking details, while the separate local administrator panel can inspect and manage records.
- The actual deployed graph, SDK-backed API, SQLite, Chroma, PostgreSQL, Redis, and simple frontend complete the walkthrough together.

## Definition of Done

- Every v1 requirement maps to exactly one roadmap phase and has executable or explicitly documented review evidence.
- Appropriate pytest unit/integration checks pass without modifying the real fixture or accidentally triggering seed/embedding side effects.
- Real Chroma retrieval and the deployed SDK/server integration are exercised; mocks alone do not establish those capabilities.
- Required live checks that were skipped, missing configuration, and deployment limitations are reported accurately.
- The local setup and core customer/admin journey are reproducible from the documented instructions.

## Traceability

All approved v1 requirements are assigned to exactly one owning phase in the user-approved Vertical MVP roadmap. No implementation is complete.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GRAPH-01 | Phase 1 | Pending |
| GRAPH-02 | Phase 1 | Pending |
| GRAPH-03 | Phase 1 | Pending |
| GRAPH-04 | Phase 1 | Pending |
| GRAPH-05 | Phase 2 | Pending |
| GRAPH-06 | Phase 1 | Pending |
| RAG-01 | Phase 2 | Pending |
| RAG-02 | Phase 1 | Pending |
| RAG-03 | Phase 2 | Pending |
| RAG-04 | Phase 2 | Pending |
| RAG-05 | Phase 1 | Pending |
| RAG-06 | Phase 2 | Pending |
| RAG-07 | Phase 1 | Pending |
| BOOK-01 | Phase 3 | Pending |
| BOOK-02 | Phase 3 | Pending |
| BOOK-03 | Phase 3 | Pending |
| BOOK-04 | Phase 2 | Pending |
| BOOK-05 | Phase 2 | Pending |
| BOOK-06 | Phase 3 | Pending |
| BOOK-07 | Phase 3 | Pending |
| BOOK-08 | Phase 3 | Pending |
| BOOK-09 | Phase 4 | Pending |
| BOOK-10 | Phase 4 | Pending |
| PRIV-01 | Phase 1 | Pending |
| PRIV-02 | Phase 3 | Pending |
| PRIV-03 | Phase 2 | Pending |
| PRIV-04 | Phase 3 | Pending |
| PRIV-05 | Phase 1 | Pending |
| PRIV-06 | Phase 4 | Pending |
| API-01 | Phase 1 | Pending |
| API-02 | Phase 2 | Pending |
| API-03 | Phase 4 | Pending |
| API-04 | Phase 4 | Pending |
| API-05 | Phase 1 | Pending |
| UI-01 | Phase 3 | Pending |
| UI-02 | Phase 2 | Pending |
| UI-03 | Phase 4 | Pending |
| UI-04 | Phase 4 | Pending |
| DEL-01 | Phase 2 | Pending |
| DEL-02 | Phase 1 | Pending |
| DEL-03 | Phase 4 | Pending |
| DEL-04 | Phase 1 | Pending |
| DEL-05 | Phase 4 | Pending |
| DEL-06 | Phase 4 | Pending |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 2 | Pending |
| TEST-04 | Phase 3 | Pending |
| TEST-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 49 total
- Mapped to phases: 49 (Phase 1: 14; Phase 2: 12; Phase 3: 10; Phase 4: 13)
- Unmapped: 0
- Duplicate assignments: 0
- Implementation complete: 0; roadmap approved

---
*Requirements defined: 2026-11-10*
*Last updated: 2026-11-10 after approval of all 49 v1 requirements and the four-phase Vertical MVP roadmap*

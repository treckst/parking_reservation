# Roadmap: Parking Reservation Assistant

## Overview

Deliver the approved 49-requirement local demo as four Vertical MVP slices: persistent policy chat, live availability with a slot grid, conversational pending requests, then administrator decisions and customer cancellation. Each slice includes the runtime, data, API, interface, and verification needed for its usable outcome. SQL remains authoritative for booking facts; Chroma supplies supported policy evidence.

**Roadmap status:** APPROVED by the user on 2026-11-10. All 49 requirements and Vertical MVP delivery are approved; no implementation or phase plans are complete.
**Delivery mode:** mvp
**Granularity:** standard

## Phases

**Phase Numbering:** Integer phases are planned milestone work. Decimal phases are reserved for later insertions and execute between their surrounding integers.

- [ ] **Phase 1: Persistent Grounded Policy Chat** - Ask supported policy questions through a deployed, session-scoped chat with persistent conversation and safe replies.
- [ ] **Phase 2: Live Availability and Slot Grid** - Compare current SQL availability and hourly prices for an explicit interval in chat and a simple grid.
- [ ] **Phase 3: Conversational Pending Reservations** - Collect and correct booking details, then acquire one valid pending hold safely across races and retries.
- [ ] **Phase 4: Administrator Decisions and Cancellation** - Resolve or cancel bookings through separate local surfaces and keep chat and grids consistent with persisted outcomes.

## Phase Details

### Phase 1: Persistent Grounded Policy Chat
**Goal:** As a customer, I want to ask policy questions, so that I can plan parking using supported answers.
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-06, RAG-02, RAG-05, RAG-07, PRIV-01, PRIV-05, API-01, API-05, DEL-02, DEL-04
**Success Criteria** (what must be TRUE):
  1. A customer can ask a supported policy question in the local chat and receive an evidence-backed answer from the deployed graph through the FastAPI SDK-backed endpoint, with validated input/output schemas and the configured `gpt-6-luna` model.
  2. Unsupported policy questions receive a clear no-available-information answer; unavailable model, embedding, retrieval, or server prerequisites produce explicit failures rather than fabricated answers or silent substitutions. Policy-only questions do not run SQL availability retrieval.
  3. A customer can continue the same session-bound thread after later questions and a graph-server restart without losing messages or earlier query evidence; concurrent submissions to that thread are controlled without mixing replies or query identities.
  4. Attempts to expose hidden instructions, another session's conversation, sensitive records, or internal graph state cannot produce an unauthorized customer reply or tool action; the final reply passes the output guardrail.
  5. A local operator can build and start the policy-chat slice with persistent graph infrastructure, observe Chroma/PostgreSQL/Redis readiness before graph startup, and exercise the actual Agent Server and SDK transport using documented configuration.
**Plans:** TBD
**UI hint:** yes

**Slice order:** Resolve the model, embedding, runtime/import, and Agent Server prerequisite gates first. Build and start the graph image from deployment JSON and declared dependencies before adding the FastAPI `langgraph_sdk` chat hookup. Then expose the minimal customer chat and verify the deployed path; an in-process graph or development-server-only check does not establish this slice.

**Planning gates:**
- Verify existing account access to the exact configured model, structured outputs, pinned dependencies, and Agent Server entitlement. Resolve the reported NumPy/Chroma import failure. Missing prerequisites remain explicit configuration gates; do not create accounts/API keys or substitute a model or deployment architecture.
- Establish embedding provenance and supported policy scope before querying. Preserve the original collection; a separately versioned rebuild requires an explicit compatibility plan and reviewed retrieval evidence.
- Decide browser-session lifetime, new-chat behavior, server-bound thread association, durable query/submission identity, and same-thread serialization versus explicit rejection. Booking ownership later reuses this boundary.
- Establish safe chat projections, customer error handling, and reviewed policy/source/page cases. Reserve the full live-availability outcome taxonomy for Phase 2.

**Verification scope:** Real Chroma source/page retrieval, structured judge/abstention, deployed SDK calls, restart continuity, request/response boundaries, same-thread contention, input/output injection handling, and cross-session thread denial. Introduce reproducible setup instructions and readable module/schema boundaries now; extend them with each slice.

### Phase 2: Live Availability and Slot Grid
**Goal:** As a customer, I want to see live slot availability, so that I can choose a suitable parking interval.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** GRAPH-05, RAG-01, RAG-03, RAG-04, RAG-06, BOOK-04, BOOK-05, PRIV-03, API-02, UI-02, DEL-01, TEST-03
**Success Criteria** (what must be TRUE):
  1. A customer can request a supported period and slot type, receive free-slot choices and PLN/hour prices from current SQL, and see matching results in the grid for that same period. A later request refreshes SQL instead of reusing older availability or the seed snapshot.
  2. The grid clearly displays its selected period and each slot's Available, Occupied, or Pending state, with EV capability visible independently of that state; customer results and errors contain no unrelated reservation PII.
  3. Availability questions combine the dedicated parallel SQL and vector results before evidence assessment. Reversed branch completion order, retried updates, and later questions preserve one merged result per query plus earlier query evidence without allowing historical facts to override current SQL.
  4. Customers can distinguish invalid time/type/inventory criteria, unsupported dates, a successful search with no free slots, insufficient evidence, and a dependency failure. Europe/Warsaw time semantics, working hours, and inventory limits are applied consistently.
  5. Existing fixture records and daily slot identities remain intact and usable after a repeatable migration; the schema supports `PENDING` and valid bookings on existing November 11–30 inventory without inventing additional inventory.
**Plans:** TBD
**UI hint:** yes

**Planning gates:**
- Decide interval endpoints, same-day scope, canonical timestamps and Europe/Warsaw offset/DST handling, historical blocking-status mappings, public/internal status spelling, and past-time/demo-clock behavior before migration and availability calculations.
- Decide slot-type matching and selected grid default date/period, the meaning of Occupied, status priority/legend, and the refresh-latency expectation that Phase 4 must satisfy. EV remains an independent attribute.
- Define partial-source failure behavior and supported policy/inventory coverage; a failed required branch must not appear as an empty successful search.
- Establish and verify the preserving migration before any later booking writes. Keep test databases isolated and avoid import-time seed/embedding side effects.

**Verification scope:** Preserved 1,440 daily slots, 720 original reservations, keys/values and relational integrity; migration reruns; time/hours/inventory boundaries; current SQL prices and overlaps; both parallel completion orders and duplicate updates; no-slot versus dependency failures; reviewed real-Chroma routing/judging/source cases; EV rendering across all statuses. Pending display may use isolated migrated test data before customer writes exist.

### Phase 3: Conversational Pending Reservations
**Goal:** As a customer, I want to request a booking in chat, so that a valid parking interval is held for approval.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** BOOK-01, BOOK-02, BOOK-03, BOOK-06, BOOK-07, BOOK-08, PRIV-02, PRIV-04, UI-01, TEST-04
**Success Criteria** (what must be TRUE):
  1. A customer can use chat and quick-action prompts to supply Name, Surname, Car Number, Zone/Slot, and Reservation Period over several turns, receive requests for missing details, and correct a field without losing other valid details.
  2. Malformed or unsupported plates and invalid booking criteria receive useful feedback before a write; changing the slot or period forces fresh availability and validation instead of reusing an earlier check.
  3. A valid request reports success only after one `PENDING` reservation commits. Its interval then appears held in fresh SQL availability and the grid, and stays held until an administrator decision or authorized cancellation.
  4. Competing sessions cannot both obtain overlapping holds; replaying the same operation after a graph retry or lost response returns its persisted result without creating a second booking or reporting an uncommitted success.
  5. A customer can access only the conversation, draft, and reservation state bound to the server-validated browser session. Supplying another session's thread/reservation ID or plate, or injecting instructions, cannot bypass scoped access, bounded ORM operations, or deterministic booking rules.
**Plans:** TBD
**UI hint:** yes

**Planning gates:**
- Decide supported plate formats and normalization, zone-only requests versus explicit slot selection, and ambiguity prompts; reuse the Phase 2 time/type/status rules.
- Define durable booking-operation keys, request fingerprints, replay/conflict responses, and recovery after commit with lost acknowledgement. Distinguish operation identity from a new query or customer correction.
- Define booking ownership and safe draft/reservation projections using the session boundary established in Phase 1; verify persistence and cross-session denial before enabling writes.
- Gate the first booking write on the preserving migration and tested shared booking service: validation, atomic interval recheck/insert, pending blocking, deduplication, SQLite locking/busy behavior, and the shared-directory topology. Verify races using independent connections/processes; model/network calls remain outside the allocation transaction.

**Verification scope:** Isolated transaction/concurrency/replay checks plus multi-turn field collection and correction, persistent thread continuity, reducer history/merge behavior, same-thread contention, user/document injection, and cross-session draft/booking isolation. Add immediate grid refresh for committed chatbot creations; the complete cancellation/admin/cross-tab refresh requirement is owned by Phase 4.

### Phase 4: Administrator Decisions and Cancellation
**Goal:** As an administrator, I want to resolve pending requests, so that customers have an accurate booking outcome.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** BOOK-09, BOOK-10, PRIV-06, API-03, API-04, UI-03, UI-04, DEL-03, DEL-05, DEL-06, TEST-01, TEST-02, TEST-05
**Success Criteria** (what must be TRUE):
  1. An administrator can inspect SQL reservation records in a separate local panel and approve a pending request as `CONFIRMED` or reject it as `CANCELLED`; invalid, repeated, or racing decisions produce controlled results and cannot resurrect a cancelled booking.
  2. A customer can cancel an allowed booking using its reservation ID and plate together with the validated session scope, releasing its hold without revealing unrelated bookings; disallowed and ownerless-fixture cases follow the explicitly chosen policy.
  3. After committed chatbot booking/cancellation transactions or administrator decisions, the grid refreshes automatically, including a separate local tab. Confirmation keeps the interval blocked, rejection/cancellation releases it, and later chat responses reflect the persisted SQL status.
  4. A local operator can reproduce the complete Compose startup and customer/admin journey using the deployed graph, SDK-backed API, frontend, Chroma, PostgreSQL, Redis, and one shared operational SQLite database. Data survives relevant service restarts; administrator surfaces remain separate and internal graph services cannot bypass the customer boundary.
  5. A developer can reproduce the isolated pytest checks and deployed walkthrough from the setup instructions and assess the result from clear code/schema boundaries and verification evidence. Deterministic results, configured live-model checks, prerequisite failures, and skipped live checks are reported distinctly, without committed credentials.
**Plans:** TBD
**UI hint:** yes

**Planning gates:**
- Decide cancellation of ownerless seeded bookings and exact repeat/conflict responses; an ID or plate alone never authorizes customer access.
- Define allowed administrator transitions, repeat/race handling, and SQL-to-chat status reconciliation. A pending request does not by itself require an indefinite graph interrupt.
- Choose a simple cross-tab refresh mechanism that meets the Phase 2 latency expectation and preserves the selected interval and independent EV display.
- Confirm single-host shared SQLite directory/sidecar permissions, locking and recovery across graph/API containers; local trusted bindings and internal graph access; and reproducible final startup/configuration instructions.

**Verification scope:** Complete isolated pytest coverage of overlaps, boundaries, holds, retries, approval/cancellation races, REST schemas/status codes/privacy, deployed SDK transport, and all customer/admin routes. Exercise the actual Chroma and deployed services in the local walkthrough, inspect cross-tab refresh and restart consistency, and review clear names, small functions, explicit schemas, and simple module boundaries. Default tests must not mutate the real fixture or trigger accidental paid ingestion; skipped live checks remain unverified.

## Coverage and Scope Rules

All **49/49** approved v1 requirements map to exactly one owning phase: Phase 1 **14**, Phase 2 **12**, Phase 3 **10**, Phase 4 **13**. No requirements are orphaned, duplicated, deferred, or added.

The owning phase completes and verifies a requirement. Earlier slices must implement any prerequisite portions before exposing their capability: session/privacy boundaries start with policy chat, SQL validation starts with availability, documentation and focused verification accompany every slice, and the final phase completes the full endpoint/lifecycle/deployment checks. A later ownership assignment does not postpone safety or correctness needed by an earlier slice.

Keep the approved scope: local trusted demo, LangChain/LangGraph only, the configured `gpt-6-luna`, SQLite bookings and PostgreSQL graph persistence. Do not add accounts/API keys, public deployment, payments, automatic hold expiry, another agent framework, silent model substitution, or invented inventory/policies. Unresolved product semantics above are planning gates, not implicit defaults.

## Progress

**Execution Order:** Phase 1 → Phase 2 → Phase 3 → Phase 4. Phase 1 is ready for discussion and planning.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Persistent Grounded Policy Chat | 0/TBD | Not started | - |
| 2. Live Availability and Slot Grid | 0/TBD | Not started | - |
| 3. Conversational Pending Reservations | 0/TBD | Not started | - |
| 4. Administrator Decisions and Cancellation | 0/TBD | Not started | - |

---
*Created and approved: 2026-11-10; ready for Phase 1 discussion and planning, with zero implementation progress.*

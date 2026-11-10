# Parking Reservation Assistant

## What This Is

A local parking reservation demo for customers and administrators, built on the repository's existing SQLite fixtures and Chroma policy documents. Customers use a simple chat interface and live slot grid to ask questions, check availability and pricing, and request or cancel bookings. Administrators use a separate bookings panel and API routes to inspect reservations and approve or reject pending requests.

The reservation application, graph, API, and frontend are planned work; the current implementation provides fixture generation, document ingestion, and a Chroma service definition.

## Core Value

Customers can request a valid parking reservation through conversation, with accurate availability, no overlapping bookings, administrator approval, and no disclosure of other customers' personal details.

## Requirements

### Validated

Existing capabilities inferred from the codebase map and read-only database inspection; these establish the starting point rather than evidence of a shipped reservation application.

- ✓ Generate deterministic SQLite parking and reservation fixtures with parameterized inserts, relational constraints, and preservation of existing rows on reruns — existing `ingested_mock_data/seed_database.py`.
- ✓ Provide 48 physical spots across four fictional facilities, represented by 1,440 daily slot records and 720 seeded reservations — existing SQLite artifact, inspected during initialization.
- ✓ Generate a corpus of 12 fictional facility and policy PDFs, three pages per document — existing `ingested_mock_data/generate_pdfs.py`.
- ✓ Ingest whole PDF pages into Chroma with stable source/page identifiers and source metadata — existing `ingested_mock_data/seed_vector_ingest.py`; the running collection contains 36 records with 1,536-dimensional embeddings.
- ✓ Run Chroma locally with persistent Docker storage — existing `docker/compose.yaml`; the service was started and its persisted collection inspected during initialization.

### Active

#### Stateful conversational graph

- [ ] Use LangChain and LangGraph as the only agent frameworks. Create the LLM directly with `llm = ChatOpenAI(model="gpt-6-luna")`; no provider identifier or live authentication preflight is required.
- [ ] Define explicit graph input and output schemas, a typed main state, and structured schemas for intent classification, evidence assessment, and booking details.
- [ ] Maintain short-term conversation and booking memory within `thread_id`, with persistence suitable for the deployed graph server.
- [ ] Keep retrieved evidence per query index within each thread. A custom reducer must merge vector documents and SQL results for the same query while preserving previous queries when a new message arrives.
- [ ] Ensure parallel retrieval updates cannot overwrite each other and retries do not duplicate evidence or booking writes.
- [ ] Classify intent into policy/general lookup, live availability/pricing, and reservation management; include a structured `check_availability` decision to control retrieval routing.
- [ ] For policy/general questions, retrieve from Chroma in a dedicated vector node. For availability questions, run separate vector and SQL retrieval nodes in parallel and join their results.
- [ ] Use SQL as the authoritative source for live availability and pricing; use vector documents for policies and general facility information.
- [ ] Use an LLM judge with structured output and conditional edges to determine whether the retrieved documents and records support an answer. Return a clear no-available-information response when they do not.
- [ ] Retain historical retrieval evidence without treating previous availability results as current; refresh SQL facts for a new availability request and before reservation writes.

#### Booking collection, validation, and approval

- [ ] Collect Name, Surname, Car Number, Zone/Slot, and Reservation Period across turns, asking for missing details without discarding information already supplied.
- [ ] Validate license plate format, start/end timestamps, facility working hours, slot existence/type, and overlapping reservations before accepting a request.
- [ ] Implement `check_availability(start_time, end_time, spot_type)` using parameterized queries through a small ORM-backed data layer.
- [ ] Implement `create_reservation(name, surname, car_number, slot_id, start_time, end_time)` as a transaction that creates a `PENDING` booking and holds the slot.
- [ ] Implement `cancel_reservation(reservation_id, car_number)` with scoped access checks and a controlled status update.
- [ ] Prevent overlapping active holds and confirmed bookings, including concurrent requests and graph retries. Recheck the interval within the reservation transaction.
- [ ] Allow an administrator to confirm a pending request or reject it by changing its status to `CANCELLED`. Rejection and cancellation release its hold.
- [ ] Preserve existing fixture records while migrating schema restrictions that currently exclude `PENDING` and reservations beyond November 10, 2026.

#### Privacy and guardrails

- [ ] Apply input filters for prompt injection attempts, including attempts to expose other customers' bookings or bypass tool restrictions.
- [ ] Treat retrieved documents and user messages as untrusted input; neither may authorize arbitrary SQL, change tool permissions, or trigger writes outside the booking workflow.
- [ ] Limit SQL tools and customer API responses to the fields needed for their purpose; do not expose other users' names, license plates, bookings, or internal graph state.
- [ ] Run outgoing replies through a guardrail node that removes or blocks unauthorized sensitive information before returning to the customer.
- [ ] Scope customer conversations and reservation state to their session/thread. A client-supplied thread or reservation identifier must not alone grant access to another customer's data.
- [ ] Keep administrator record access on separate routes and in the administrator panel. No customer/admin login or API keys are required for this local trusted demo; distinct routes are organization, not authentication.

#### REST API and deployment

- [ ] Package the graph as an Agent Server image with LangGraph deployment JSON and dependency specifications before adding the SDK-backed application API.
- [ ] Implement the application API in FastAPI, using `langgraph_sdk` to run the deployed graph rather than invoking an in-process graph as the deployed chat path.
- [ ] Provide `POST /api/chat` accepting a message and `thread_id`, returning the assistant reply and a safe projection of the updated reservation state.
- [ ] Provide `GET /api/slots` returning slots and their computed availability from SQL. Define interval/date selection explicitly rather than presenting the seed's snapshot flag as live truth.
- [ ] Provide `GET /api/reservations` for the administrator bookings view, and `PATCH /api/reservations/{id}` for administrator status changes to `CONFIRMED` or `CANCELLED`.
- [ ] Enforce Pydantic request/response schemas, appropriate HTTP status codes, configured CORS, and parameterized ORM queries.
- [ ] Build Docker Compose orchestration for Chroma, the graph server, PostgreSQL, Redis, the application API, and the simple frontend as needed.
- [ ] Require Chroma readiness before the graph server starts. Configure PostgreSQL and Redis readiness dependencies, persistent storage, and service addresses suitable for containers.
- [ ] Keep SQLite as the booking database and a separate SQLite database with exact `SqliteSaver` for conversation checkpoints. Own its connection outside the graph in a local variable/closure, never runtime context. PostgreSQL/Redis support graph-server infrastructure. Both the graph booking tools and REST administration endpoints must use the same booking data and transaction rules.
- [ ] Document repeatable local setup, image build, startup, configuration, and verification steps without committing credentials.

#### Simple interactive frontend

- [ ] Provide a customer chat panel with quick-action prompts for policy questions, availability checks, and reservation requests.
- [ ] Provide a simple visual slot grid showing availability, occupancy, pending holds, and EV capability; EV is a slot attribute that must remain visible alongside its availability status.
- [ ] Automatically refresh the slot grid after chatbot SQL transactions and administrator status changes so it reflects persisted booking state.
- [ ] Provide a separate administrator bookings panel to inspect reservation records and approve or reject pending requests.
- [ ] Keep frontend presentation simple and make missing information, validation failures, pending approval, and booking results understandable.

#### Quality and verification

- [ ] Keep code readable and self-explaining through clear names, small functions, explicit schemas, and simple module boundaries. Add comments where they explain a decision or constraint; avoid unnecessary abstraction and excessive commentary.
- [ ] Write pytest unit and integration tests for SQL overlap detection, booking validation, pending holds, approval/cancellation, and concurrent reservation attempts.
- [ ] Test REST endpoint behavior, request/response validation, error status codes, SDK integration, and customer/admin response boundaries.
- [ ] Test vector retrieval accuracy with representative questions and expected policy sources, plus the judge's no-information behavior and parallel retrieval routing.
- [ ] Test multi-turn slot filling, thread isolation, per-query reducer retention/merging, and prompt-injection/PII guardrails.
- [ ] Verify the deployed graph, API, and frontend work together against the Docker services. Mock OpenAI calls in automated tests so they run without provider credentials or live API requests; do not enforce live provider preflight checks.

### Out of Scope

- Customer/admin accounts, login flows, and API-key authentication — the agreed v1 is a local trusted demo with separate customer and administrator surfaces.
- Public production exposure without an access-control design — route separation does not enforce administrator privileges or establish customer identity.
- Payments, payment-provider integration, and automatic refunds — the current scope covers pricing information and booking management.
- Additional agent frameworks — orchestration is restricted to LangChain and LangGraph.
- A complex dashboard, advanced design system, or native mobile application — the frontend should remain very simple.
- Replacing SQLite bookings with PostgreSQL as part of the initial deployment — PostgreSQL is needed for graph-server infrastructure; SQLite remains the requested operational booking source.

## Context

### Existing repository and verified data

- Python >=3.12 with uv-managed dependencies. The declared stack includes LangChain, LangGraph, Pydantic, Chroma, OpenAI integrations, and PDF loading; no application implementation currently exists in `src/`.
- The complete codebase map is in `.planning/codebase/`, dated November 9, 2026. Read its architecture, stack, and concerns before planning implementation.
- The SQLite fixture is `ingested_mock_data/parking_november_2026.sqlite3`. Initialization checks returned `integrity_check = ok`, zero foreign-key violations, 1,440 slot rows, 720 reservations, and zero overlapping non-cancelled reservation pairs.
- Slots cover November 1–30, 2026; seeded reservations cover November 1–10. The reservation table currently accepts only lowercase `confirmed`, `active`, `completed`, and `cancelled` statuses and enforces same-day intervals.
- Daily slot identity is `(spot_id, slot_date)`. Facility prefixes are CTR, RIV, STA, and AIR; spot types are standard, electric, accessible, and van. Prices are PLN/hour and working hours are 06:00–22:00.
- `current_availability` is a fixed November 9, 2026 noon snapshot, not an interval-availability guarantee. Live availability must derive from booking intervals and blocking statuses.
- The Chroma `parking_documents` collection was inspected over HTTP after starting the existing service. It contains 36 pages from 12 PDF sources, with source/page metadata and 1,536-dimensional vectors.
- Use embeddings directly with `embeddings = OpenAIEmbeddings(check_embedding_ctx_length=False)`, matching the ingestion script's library defaults. No embedding model override, provenance file, or provenance verification gate is required; preserve the existing Chroma collection.
- PDFs and fixture people, plates, locations, and policies are fictional. The source corpus is effective for November 2026; answers and availability must respect data coverage instead of implying unlimited dates.
- The local Python Chroma client failed to import because NumPy's C extensions could not load; direct HTTP inspection succeeded. Resolve or reproduce this environment issue during implementation setup.
- Seed and ingestion scripts run at import time. Tests must not import them in a way that writes the real fixture or triggers embedding calls; introduce explicit entry points if helpers are reused.

### Workflow and behavior details to settle during phase planning

- Use `ChatOpenAI(model="gpt-6-luna")` and `OpenAIEmbeddings(check_embedding_ctx_length=False)` directly. Test provider interactions with mocks and report runtime service errors safely; do not block implementation on live authentication or provenance checks.
- Define plate normalization and supported formats for the supplied Polish-style fixtures, with clear validation messages.
- Define date/time parsing and timezone behavior using Europe/Warsaw. Preserve the existing data's offset semantics and test boundary cases.
- Define the selected interval/date used by the live slot grid, how occupied and pending states are derived, and behavior outside seeded inventory dates.
- Define the public/internal spelling of statuses and how legacy fixture statuses map to the booking lifecycle.
- Define safe browser session/thread association without customer login, and keep the no-auth administrator surface within the trusted local deployment boundary.
- Define how API administrator decisions update or resume any interrupted graph run so chat and database state remain consistent.
- Pending holds last until an administrator decision or cancellation in the agreed scope; automatic expiry is not yet specified.

## Constraints

- **Agent stack**: Use only LangChain and LangGraph for agent orchestration — explicit user requirement.
- **Application LLM**: Use exactly `llm = ChatOpenAI(model="gpt-6-luna")` without identifier/authentication preflight — explicit user choice.
- **Embeddings**: Use exactly `embeddings = OpenAIEmbeddings(check_embedding_ctx_length=False)` without model/provenance configuration gates — explicit user choice.
- **Storage**: Reuse existing Chroma documents and SQLite booking data; add PostgreSQL and Redis for the graph server — preserve the current assets and requested deployment shape.
- **Memory**: Preserve retrieved evidence per query in a thread using a custom reducer — later turns must not clear previous retrieval results.
- **Correctness**: Pending bookings hold slots, and reservation writes must prevent overlaps transactionally — an availability read alone cannot prevent a race.
- **Privacy**: Customer paths must not expose another customer's PII or reservations — filters must be backed by scoped data access and response schemas.
- **Access model**: No customer/admin login or API keys; use separate endpoints and UI surfaces within a local trusted demo — explicitly agreed during discovery.
- **Deployment**: Build and deploy the graph server image before the SDK-backed REST integration; use Compose readiness dependencies so Chroma is available before the graph starts.
- **Maintainability**: Prefer readable, self-explaining code without overloading it — explicit user preference.
- **Testing**: Supply pytest unit and integration coverage for SQL overlaps, REST endpoints, and RAG accuracy, including the critical state and privacy behavior.
- **Lean workflow**: Execute inline, disable optional research, verification and code-review subagents, and retain focused executable tests. No live OpenAI preflight checks.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Include a simple customer chat, live slot grid, and administrator bookings panel in v1 | User expanded the initial API-only scope with explicit frontend requirements | — Pending |
| Use separate customer/admin endpoints without login or API keys | User explicitly rejected customer/admin API keys and selected separate interfaces | — Pending; local trusted demo boundary |
| `PENDING` bookings hold their requested interval | User explicitly chose pending holds to prevent competing bookings | — Pending |
| Reject pending requests through `CANCELLED` status and release the hold | Fits the requested administrator PATCH status values and rejection workflow | — Pending |
| Keep SQLite for operational bookings and PostgreSQL for graph persistence | Reuses the requested SQL source while supporting the graph-server deployment | — Pending |
| Route availability questions to parallel vector and SQL nodes | Combines policy context with live slot facts using explicit graph routing | — Pending |
| Preserve evidence by query index with a custom reducer | Prevents later questions or parallel nodes from clearing earlier retrieval results | — Pending |
| Use an evidence judge and conditional no-information branch | Unsupported answers must not be fabricated from inadequate retrieval | — Pending |
| Put FastAPI on top of `langgraph_sdk` and a deployed graph image | Explicit user requirement for server/API separation and deployment order | — Pending |
| Keep code and frontend simple | Readability and a minimal usable interface matter more than framework or UI complexity | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Move invalidated requirements to Out of Scope with a reason.
2. Move verified requirements to Validated with a phase reference.
3. Add newly discovered requirements to Active.
4. Record decisions and their observed outcomes.
5. Update What This Is to match the implemented product.

**After each milestone** (via `$gsd-complete-milestone`):
1. Review all sections against the delivered application.
2. Confirm that the Core Value still sets the right priority.
3. Review Out of Scope boundaries and their reasons.
4. Update Context with current behavior, users, verification, and known limitations.

---
*Last updated: 2026-11-10 after project discovery and approval to create PROJECT.md*

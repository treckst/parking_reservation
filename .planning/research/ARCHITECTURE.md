# Architecture Research

**Project:** Parking Reservation Assistant  
**Domain:** Local conversational parking reservations with human approval  
**Researched:** 2026-11-10, Europe/Warsaw  
**Confidence:** MEDIUM — verified official documentation; proposed integration has not been implemented or exercised.

## Recommended Architecture

Use one explicit LangGraph `StateGraph` for conversational orchestration, LangChain model/retriever adapters, a separate FastAPI application calling the deployed Agent Server through `langgraph_sdk`, and one shared Python booking service. SQLite owns operational booking truth; graph checkpoints own conversation continuity and historical evidence. Keep the application within its agreed local trusted deployment boundary.

The repository currently contains fixture and ingestion scripts, an empty application source location, and a Chroma Compose service. This is a proposed architecture, not a description of implemented application behavior. Existing inventory has composite daily identity `(spot_id, slot_date)` and a snapshot availability flag; current bookings must be computed from intervals.

### Component and deployment diagram

```text
Browser: customer chat + interval slot grid        Local administrator panel
                    |                                      |
                    +------------- HTTP -------------------+
                                       |
                          FastAPI application boundary
                    request/session checks; safe response DTOs
                     /api/chat          /api/slots; reservations
                          |                         |
                   langgraph_sdk                    |
                          |                         |
                 Private Agent Server               |
                  LangGraph StateGraph              |
                 /          |          \            |
          LangChain LLM  vector node  SQL/tools -----+
               |            |          |
        configured model   Chroma      shared booking service package
                                        |
                              booking_data volume directory
                              /data/bookings.sqlite3

Agent Server ---- PostgreSQL: threads, runs, checkpoints
             \--- Redis: worker coordination and ephemeral metadata
FastAPI session/thread associations ---- shared booking SQLite application tables
```

Both graph tools and REST booking routes use the same installed booking package and the same absolute SQLite path. Mount the **directory**, including SQLite journal/WAL sidecars, into both containers on the same local Docker host. Never bake independently writable database copies into their images. PostgreSQL is Agent Server infrastructure; adding it does not migrate parking records. Redis is not the durable booking or conversation store. These infrastructure roles are documented in [LangSmith data plane](https://docs.langchain.com/langsmith/data-plane).

| Component | Owns | Boundary |
|-----------|------|----------|
| Frontend | Chat, selected interval, grid, separate admin view | Calls only the application API; no model/provider secrets |
| FastAPI | Pydantic HTTP contracts, browser session/thread binding, SDK calls, administrative routes, safe projections | Does not invoke the deployed graph in process |
| Graph | Input/output guardrails, structured router, slot filling, retrieval branches, evidence judge, response composition | Calls only fixed domain tools; customer cannot select graph IDs or inject runtime context |
| Booking service | Validation, interval availability/pricing, lifecycle, ownership, idempotency and transaction policy | Shared by graph tools and REST routes |
| SQLite | Inventory, reservations, owner/session associations, durable operation keys | Authoritative for every booking status and hold |
| Chroma | Policy/facility pages with source/page metadata | Evidence only; cannot authorize SQL or override live records |
| Agent Server/PostgreSQL | Runs, thread state and checkpoint persistence | Internal service; raw state/history endpoints are not customer API |

### Suggested source structure

```text
src/parking/
  domain/       # schemas, lifecycle, interval/time/plate validation
  bookings/     # ORM models, repository, transactions, ownership, migrations
  graph/        # state, reducers, structured schemas, nodes, topology, export
  retrieval/    # Chroma adapter, metadata/evidence normalization
  api/          # FastAPI app, HTTP DTOs, sessions, SDK gateway, routes
  settings.py   # typed environment settings; separate service addresses
tests/          # temporary DB, graph, API, deployment and live-model suites
langgraph.json  # exported graph and dependency/environment configuration
docker/         # Compose, images, health probes
```

Keep fixture scripts as explicit commands. Their current import-time execution must not become an application initialization path or test import.

## State and Graph Contracts

Use explicit `TypedDict` input, output and main state schemas. Pydantic validates externally supplied HTTP data and model-produced router/extraction/judge objects; type hints alone do not validate them. The framework supports separate input/output schemas and per-channel reducers. Crucially, private channels and output schemas do **not** hide raw streaming updates by default. [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api)

The following is a proposed contract sketch, not a drop-in complete implementation:

```python
from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

class GraphInput(TypedDict):
    message: str
    request_id: str  # stable across a retry of this user submission

class ReservationView(TypedDict):
    reservation_id: str | None
    status: str | None
    missing_fields: list[str]

class GraphOutput(TypedDict):
    reply: str
    reservation: ReservationView
    bookings_changed: bool

class RouteDecision(BaseModel):
    intent: Literal["policy", "availability", "reservation"]
    check_availability: bool

class BookingDraft(BaseModel):
    name: str | None = None
    surname: str | None = None
    car_number: str | None = None
    slot_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None

class EvidenceAssessment(BaseModel):
    verdict: Literal["supported", "no_information", "clarify"]
    evidence_ids: list[str]
    missing_information: list[str]

class MainState(GraphInput, GraphOutput, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    query_index: int
    request_queries: dict[str, int]
    route: RouteDecision
    draft: BookingDraft
    evidence: Annotated[dict, merge_evidence]
    assessment: EvidenceAssessment
    operation_id: str
    owned_reservation_id: str | None

# merge_evidence is the pure function defined in the reducer section.
builder = StateGraph(
    MainState, input_schema=GraphInput, output_schema=GraphOutput
)
```

Define concrete nested evidence types in implementation; the abbreviated `dict` above keeps the sketch readable. Carry the trusted session owner in server-controlled runtime context, not user-editable graph input. Initialize defaults explicitly. Only the turn-initialization node increments the query index, after checking `request_id` reuse. Persist this turn identity before any write node.

Use `model.with_structured_output(RouteDecision)`, similarly for booking extraction and evidence assessment. Validate route consistency deterministically: availability intent requires `check_availability=True`; unavailable parameters produce clarification rather than an unbounded query. Provider structured-output support and the requested `gpt-6-luna` identifier remain an implementation gate, with no silent model replacement. The standalone model interface supports Pydantic structured outputs; no additional agent loop is needed. [LangChain models](https://docs.langchain.com/oss/python/langchain/models#structured-output)

### Custom per-query evidence reducer

Use a nested immutable evidence map:

```text
evidence[query_index][source_kind][stable_result_id] = evidence_record
source_kind = vector | sql
vector record = source, page, content/revision, citation ID
SQL record = normalized interval/filter, observed_at, outcome, safe slot rows
```

Each node returns only its source's delta for the current query. The reducer copies maps and unions entries; it never clears the whole evidence map on a new message. A vector key includes the document/page revision. A SQL result represents a complete read snapshot, including an empty result, rather than a partial list appended one slot at a time.

```python
from copy import deepcopy

def merge_evidence(left, right):
    merged = deepcopy(left or {})
    for query, sources in (right or {}).items():
        target_query = merged.setdefault(query, {})
        for source, records in sources.items():
            target = target_query.setdefault(source, {})
            for result_id, record in records.items():
                if result_id in target and target[result_id] != record:
                    raise ValueError("Conflicting immutable evidence identity")
                target[result_id] = deepcopy(record)
    return merged
```

**Proposed invariant:** the same evidence identity always denotes the same immutable record. Over valid updates this is associative, commutative and idempotent, with `{}` as identity. Conflicts fail explicitly; execution order must not select an arbitrary winner. Do not replace this with list concatenation or order-dependent dictionary overwrite.

Preserve a completed retrieval snapshot when replaying a completed task; a deliberate fresh read needs a new retrieval/query identity. A retry that has not persisted any successful result may read again. Stable IDs suppress repeated delivery of an identical node update, while request deduplication stops an HTTP retry from creating another query. These guarantees are application design and require tests: associativity, reversed branch order, exact replay, historical retention, identity conflicts, and a second query receiving changed SQL facts.

The answer/judge receives **only current-query evidence**. Historical evidence remains available for conversation context, but old SQL availability never satisfies a new availability request or write validation. Serialize and deserialize the query-index keys consistently because JSON object keys are strings.

## Control Flow and Data Flow

```text
START -> initialize turn -> input guard -> refresh owned booking -> router
                                                       |
                 +-------------------------------------+-----------------+
                 |                                     |                 |
              policy                              availability       reservation
                 |                                     |                 |
          vector_policy                         validate interval    extract patch
                 |                                     |                 |
                 |                             availability_dispatch  validate draft
                 |                               /           \          |
                 |                     vector_availability  SQL       missing?
                 |                               \           /        /     \
                 |                               barrier join      ask      prepare operation
                 +---------------------------> evidence judge       |            |
                                                 /   |   \          |       transactional tool
                                           supported none clarify   |            |
                                                 \   |   /          |      reload SQL result
                                                  compose <---------+------------+
                                                     |
                                              output guard -> END
```

Register `vector_policy` and `vector_availability` as separate graph node names using the same retrieval implementation. This small duplication of topology makes the availability join unambiguous: `add_edge(["vector_availability", "sql_availability"], "judge")`. Policy uses `add_edge("vector_policy", "judge")`. Do not attach a barrier requiring SQL to the policy-only path. The two availability branches run in parallel and update only the evidence reducer channel; neither branch writes the single-writer draft, route or reply fields. Parallel routing and reducer-backed fan-in are framework-supported patterns. [Graph build checklist](https://docs.langchain.com/oss/python/langgraph/use-graph-api)

1. **Policy/general lookup:** classify, retrieve pages, judge support, compose with citations. Filter facility/date applicability. Retrieved instructions are data, never graph configuration.
2. **Availability/pricing:** clarify missing interval/type/facility, then parallel vector policy and SQL facts. SQL is authoritative for current inventory and price. A valid query returning no slots supports an explicit unavailable answer; it is not missing information. Out-of-coverage dates, retrieval failures and missing policy support are separate outcomes.
3. **Judge:** return structured verdict and supporting evidence IDs. Check IDs exist in current evidence and require successful current SQL evidence for live claims before accepting `supported`. Conditional edges send insufficient evidence to a clear no-information answer; missing user parameters lead to clarification. Limit retries on schema/model failures and return an explicit failure rather than guessing.
4. **Multi-turn booking:** extract a patch, merge only supplied fields, allow explicit correction/clearing, and validate deterministically. Ask for missing Name, Surname, Car Number, Zone/Slot and Reservation Period while preserving earlier values. Slot IDs must resolve against daily inventory; a zone alone may require a selection. Derive missing fields from the draft, not a model's claimed completeness.
5. **Write:** persist the operation identity, execute the narrow tool, then reload the owned booking and form the response from SQL. Do not make an LLM judge the authority on whether a write succeeded.

## Deterministic SQL Tools and Booking Lifecycle

Provide fixed, typed tools for `check_availability(start_time, end_time, spot_type)`, `create_reservation(name, surname, car_number, slot_id, start_time, end_time)`, and `cancel_reservation(reservation_id, car_number)`. Owner scope and operation identity are injected by application code. Use SQLAlchemy-bound parameters; do not expose arbitrary SQL generation, table browsing or general SQL execution to the model.

**Proposed transaction policy:** acquire the SQLite write reservation with `BEGIN IMMEDIATE` before overlap checking; validate, check and insert/update on that same connection and transaction, then commit. Use bounded handling for `SQLITE_BUSY`, foreign keys on every connection, and short transactions with no LLM/network work inside them. SQLite allows one simultaneous writer, and `BEGIN IMMEDIATE` takes the write transaction before the application performs its conflict read. [SQLite transactions](https://www.sqlite.org/lang_transaction.html)

The overlap predicate is `existing.start < requested.end AND existing.end > requested.start`, treating intervals as half-open so adjacent bookings are allowed. Define the blocking-status set once for all tools and grid reads. `PENDING` and `CONFIRMED` block; legacy `active` needs a documented mapping. Historical `completed` records remain occupied historical intervals when querying the past rather than being mistaken for current holds. `CANCELLED` releases the interval. Reject invalid transitions; repeating the same completed transition is harmless.

```text
validated create -> PENDING (holds interval)
PENDING -> CONFIRMED (admin approval, same held interval)
PENDING -> CANCELLED (admin rejection or scoped customer cancellation)
CONFIRMED -> CANCELLED (allowed scoped cancellation)
CANCELLED -> CONFIRMED is rejected; require a new checked request
```

Migrate the fixture's status and November 1–10 reservation constraints while preserving records and foreign keys. Public lifecycle spelling can be uppercase with explicit legacy normalization. Preserve daily composite identity and initially retain same-day reservations within 06:00–22:00; cross-day stays need a separate inventory design. Parse Europe/Warsaw times into a single comparable representation before storage/comparison. Do not compare differently offset timestamp strings as if lexical order were chronological order. Live grid reads must use the selected interval and the same conflict predicate, not `current_availability`.

SQLAlchemy's SQLite driver has transaction-control caveats; implement and integration-test an explicit transaction strategy rather than assuming a generic ORM transaction starts before the conflict query. [SQLAlchemy SQLite transactions](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#transactions-with-sqlite-and-the-sqlite3-driver)

### Replay-safe writes

Generate or derive a stable operation ID from already durable thread/turn and draft-revision state. Store an operation key, owner and request fingerprint with a unique constraint in SQLite in the **same transaction** as the booking write. A repeated matching operation returns the original booking; the same key with a different payload fails. This covers a crash after SQLite commit but before graph checkpoint acknowledgement. Do not generate a fresh UUID inside the side-effect node on every execution. The framework explicitly leaves external side-effect idempotency to application code. [LangGraph fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance#retry-boundaries-and-idempotency)

### Administrator synchronization: finish the pending turn

**Recommend ending the graph turn after persisting `PENDING`; do not leave a long-lived approval interrupt in v1.** The customer receives the booking ID and pending status immediately. Admin PATCH calls the same transactional service, conditionally changes status and increments a booking revision. Grid refreshes read SQL. Every subsequent customer turn refreshes its owned reservation before interpreting status; FastAPI also derives the returned booking projection from current SQL. A stored graph status is a cache, not authority.

This avoids pretending SQLite and PostgreSQL checkpoint writes are one atomic transaction. Do not let a best-effort admin `update_state` replace the committed SQL decision. If immediate proactive chat updates are later required, add a SQL-backed outbox and idempotent reconciliation keyed by reservation/revision. If implementation instead selects an interrupt, it must specify the durable approval event, exact interrupt/run linkage, idempotent resume, concurrency handling, and recovery after SQL commit with failed SDK resume. That is additional work, not required to display pending approval.

## Sessions, Privacy and API Integration

### Session/thread ownership without accounts

Create a random server-managed browser session cookie and bind graph thread IDs to it in a persistent application table. This is local anonymous session continuity, not customer login. `POST /api/chat` still accepts `message` and `thread_id`, but verifies the requested thread belongs to the cookie session before any SDK access; first use allocates/binds the thread server-side. Thread ID knowledge alone grants no access. Set appropriate cookie flags for the local HTTP setup and restrictive CORS/origin behavior; same-origin frontend hosting is simplest.

Persist owner scope on application-created bookings. For cancellation, require reservation ID plus normalized plate **and** matching session ownership. The plate is a requested check, not an identity secret. Seeded rows without an application owner remain available to the trusted administrator, not adoptable by supplying a plate. Cross-session booking recovery is unresolved and can remain outside v1.

### Structural privacy plus filters

Input guard blocks suspicious attempts to expose records or alter tool permissions; output guard checks every customer reply. These defenses accompany structural boundaries: SQL availability returns slot/type/price/availability only; customer booking reads use ownership predicates; no other customer's name/plate reaches the model; only fixed booking tools exist; retrieved pages cannot authorize writes. Guardrails can combine deterministic checks with model-based checks. [LangChain guardrails](https://docs.langchain.com/oss/python/langchain/guardrails)

Use explicit FastAPI response models and allowlisted projections for chat, grid and admin responses. Never proxy graph state, raw evidence, runtime context, SDK exceptions, trace URLs or unfiltered update streams to customers. Checkpoint history may contain a customer's own booking PII, so keep Agent Server internal and avoid raw tracing/logging of personal data by default. Response models provide output validation/filtering, but query scoping must prevent unauthorized data from being loaded in the first place. [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/)

### SDK-only deployed chat path

Construct/reuse the asynchronous SDK client in FastAPI lifespan and call the configured deployed graph. Create server-side threads through the SDK and use SDK run creation/wait or create/join APIs; project only the allowed output fields after completion. Persist client submission IDs so network retries can rejoin/retrieve the original run, rather than creating a new booking turn. Configure timeouts and treat missing acknowledgements as unknown completion until checked. [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [SDK thread/run example](https://docs.langchain.com/langsmith/reject-concurrent)

**Per-thread concurrency:** set `multitask_strategy="reject"` on every run and map contention to HTTP 409 with a clear busy response. Disable duplicate submissions while a turn is pending. This serializes accepted turns through Agent Server across workers; an API process-local lock alone is insufficient. Other threads may run concurrently, with SQLite transaction policy guarding shared slots. Do not use interruption/rollback as the default for a booking workflow because a committed SQL side effect cannot be undone by rolling back graph state. The documented rejection behavior preserves the active run and rejects a competing one. [Reject concurrent runs](https://docs.langchain.com/langsmith/reject-concurrent)

Admin `GET /api/reservations` and `PATCH /api/reservations/{id}` belong to a separate router/panel and may include the full administrative record. Route separation is organization, not authentication. Bind the deployment to loopback/trusted local use; keep graph, PostgreSQL and Redis unexposed on the Compose network. Do not infer admin privileges from a chat message or editable role field. No public-production account/authentication project is added here.

## Checkpoint Ownership and Service Readiness

Agent Server manages checkpoint persistence automatically. Export the deployment graph without constructing a local `InMemorySaver` or separate SQLite checkpoint database. Provide a graph factory for tests; direct graph invocations outside Agent Server compile with an explicit test saver and pass `configurable.thread_id`. Verify thread isolation and state retention across multiple calls. [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)

The image must include the graph export, `langgraph.json`, dependency metadata and configuration. Build/deploy it before adding the SDK-backed FastAPI chat path. Validate the selected standalone Agent Server build's actual credential/license prerequisites early: the current official standalone guide lists deployment credentials and license verification/egress requirements. Application no-login/no-API-key scope does not remove provider/deployment secrets. Do not silently switch to an in-process FastAPI graph if the deployment gate fails. [Application structure](https://docs.langchain.com/langsmith/application-structure), [Standalone Agent Servers](https://docs.langchain.com/langsmith/deploy-standalone-server)

| Service | Readiness/dependency policy |
|---------|----------------------------|
| SQLite initialization/migration | One explicit init job completes before graph/API; never migrate simultaneously from each worker |
| PostgreSQL | `pg_isready`; persistent volume; graph waits for healthy state |
| Redis | `redis-cli ping`; graph waits for healthy state |
| Chroma | Image-compatible HTTP heartbeat; graph waits for healthy state; verify collection/model compatibility separately |
| Agent Server | Health endpoint from chosen image plus graph load/smoke check; application waits for readiness |
| FastAPI | Readiness checks configured graph connectivity and booking DB access/schema; frontend starts against ready API |

Compose dependency ordering alone does not mean a service is ready. Use `service_healthy` and `service_completed_successfully` as appropriate, plus bounded runtime reconnect/error handling because dependencies may fail after startup. [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)

Consider WAL for simultaneous reads with short writes, but test the actual Docker volume mount and runtime SQLite version. WAL still permits one writer and requires same-host shared file access; it is unsuitable for remote/network filesystem sharing. [SQLite WAL](https://www.sqlite.org/wal.html)

## Suggested Vertical-Slice Build Order

1. **Booking truth and migration:** preserve fixture data; shared ORM/service, half-open overlaps, PENDING hold, idempotent create/cancel/admin transitions, ownership fields and selected-interval reads. Prove concurrent conflicting requests yield one hold.
2. **Graph contract and deployed policy answer:** typed schemas/reducer, structured router, vector-only retrieval, judge/no-information branch and both guards; compile with test checkpointer, then build the Agent Server image and deploy with PostgreSQL/Redis/Chroma readiness. Verify requested model and deployment entitlement now.
3. **SDK customer surface:** add FastAPI session/thread association and SDK gateway only after deployed graph works. Provide a minimal chat plus interval grid, safe response DTOs and concurrent-turn handling. This is the first complete deployed policy-answer slice.
4. **Live availability slice:** separate parallel SQL/vector nodes, explicit barrier, current-query evidence rules, pricing/coverage behavior and grid integration. Verify parallel updates survive retry and later turns retain history without using stale SQL.
5. **Reservation and approval slice:** incremental slot filling, validation, durable operation identity, pending request, cancellation, admin list/PATCH, SQL-based chat reconciliation and automatic grid refresh. Add simple polling/focus refresh across customer/admin tabs as well as refresh after the current chat's mutation.
6. **Recovery and boundary verification:** crash-after-commit replay, two-process SQLite race, SDK failure mapping, cross-session attempts, injection/PII cases, Chroma retrieval examples, no-information cases, restart persistence and complete Compose walkthrough.

Each slice delivers visible behavior and tests its own boundaries. Final integration testing does not postpone privacy, overlap, reducer or ownership verification until the end.

## Scaling and Anti-Patterns

| Concern | Local demo approach | First change if measured demand grows |
|---------|---------------------|---------------------------------------|
| SQLite writer contention | One host, shared directory, short write transaction and bounded busy handling | Reassess booking database architecture; do not add cross-host SQLite writers |
| Conversation latency | Parallel SQL/vector retrieval; bounded judge and generation | Measure model calls before adding orchestration complexity |
| Growing evidence/checkpoints | Retain per-query evidence as required; pass only relevant current evidence to prompts | Explicit session retention/archive policy; no silent deletion of required history |
| Grid consistency | Read SQL after mutation and on short polling/focus refresh | SSE/events only if actual UX needs justify them |

Avoid one large node that classifies, retrieves and writes; it obscures retry boundaries. Avoid generic SQL agents, two copied booking databases, snapshot availability flags, router booleans as authorization, arbitrary last-writer evidence merges, long-lived database transactions during LLM calls, direct customer graph-state access, and best-effort checkpoint patches as booking truth.

## Unresolved Choices and Confidence

| Choice | Recommendation / needed validation | Confidence |
|--------|------------------------------------|------------|
| Requested model and deployment entitlement | Verify actual provider model ID, structured-output support, account availability and selected Agent Server requirements before roadmap assumes deployability | MEDIUM for documented architecture; availability unresolved |
| SQLite timestamp/status migration | Explicit legacy mapping, normalized timestamp representation, same-day scope and rollback/preservation checks | MEDIUM; design proposal |
| Session capability lifecycle | Persistent browser-session ownership; define cookie expiry and thread cleanup; no plate-only adoption | MEDIUM; design proposal |
| Pending expiry | Keep pending until admin decision/cancellation per current scope; no automatic expiration inferred | MEDIUM; project decision |
| Admin-to-chat immediacy | Finish pending turn, reload from SQL next turn/response; proactive notification needs separate outbox design | MEDIUM; design proposal |
| Embedding compatibility | Confirm original ingestion model; dimensions alone do not identify it; configure same query model | MEDIUM; repository evidence |
| Two-container SQLite sharing | Named local directory volume; verify actual locking, permissions, WAL sidecars and concurrent process behavior | MEDIUM; needs deployment test |

All framework claims above were checked against direct official sources on 2026-11-10; architecture choices are explicitly recommendations/inferences. The research-plan seam selected Context7, but no Context7 MCP or `ctx7` executable was available; official web documentation was the fallback. The code seam `classify-confidence --provider websearch --verified` returned **MEDIUM**. Source pages are living documentation and may differ from the repository's locked packages, so implementation must check pinned signatures. No live-model, deployed SDK or transaction test was performed during this research.

# Project Research Summary

**Project:** Parking Reservation Assistant
**Domain:** Local conversational parking reservations with administrator approval
**Researched:** 2026-11-10 (Europe/Warsaw)
**Confidence:** MEDIUM overall; accepted scope is clear, deployment and runtime compatibility remain untested.

## Executive Summary

This is a trusted local demonstration of a complete reservation journey, built around existing fictional SQLite inventory and Chroma policies. Experts build this kind of assistant by keeping deterministic booking rules outside model reasoning: SQL decides live availability, pricing, ownership, and committed status; vector retrieval supplies policy context; the graph manages conversation and evidence. The existing fixtures are a starting asset, not a reservation application: there are 48 physical spots, 1,440 daily inventory rows, 720 reservations, and 36 policy pages, but no implemented application flow.

Use Python 3.12, uv, LangChain/LangGraph, Pydantic, a small SQLAlchemy booking service, FastAPI, and plain HTML/CSS/JavaScript. Deploy an Agent Server image with PostgreSQL and Redis before integrating chat through `langgraph_sdk`. Graph tools and administrative routes must share one booking service and one SQLite directory on one Docker host. The stack researcher verified the public `gpt-6-luna` API identifier; account access and structured-output execution remain setup gates. Keep that exact configured model and report unavailable access explicitly. Avoid additional frameworks, a frontend build system, payments, and application login/API keys.

The largest risks are concurrent overlapping holds, duplicated writes after lost acknowledgements, stale SQL evidence, historical fixture constraints, PII leakage, unknown embedding provenance, and unverified standalone-server entitlement. Mitigate them with preserving migrations, short explicit allocation transactions, durable operation keys, current-query evidence rules, scoped data access, and early pinned-runtime smoke tests. A committed `PENDING` request holds its interval until administrator decision or cancellation. End that graph turn and reconcile later responses with SQL; an indefinite approval interrupt is unnecessary. Separate administrator routes organize this local demo; they do not authorize public administration.

## Key Findings

### Recommended Stack

See [STACK.md](STACK.md) for candidate versions, compatibility metadata, configuration, and sources. Published versions are research baselines, not a successfully resolved lock or tested container set.

| Technology | Recommended baseline | Purpose and rationale |
|------------|----------------------|-----------------------|
| Python / uv | Python 3.12.x; existing uv workflow | One runtime across development and images; commit a reproducible lock. |
| LangChain / LangGraph | 1.4.9 / 1.2.20; core 1.7.7 | Explicit typed workflow, parallel retrieval, reducers, and thread memory; only agent frameworks. |
| OpenAI integration / model | `langchain-openai` 1.7.4; `gpt-6-luna` | Structured intent, extraction, judge, and replies; account availability still untested. |
| Pydantic | 2.14.3 | Validate model outputs and HTTP boundaries; schemas do not prove factual correctness. |
| SQLAlchemy / SQLite | SQLAlchemy 2.1.8; record bundled SQLite version | Small parameterized repository and explicit transactions preserving current booking assets. |
| FastAPI / Uvicorn / SDK | 0.162.2 / 0.54.0 / `langgraph-sdk` 0.4.14 | Separate HTTP boundary calling the deployed graph; safe response projections. |
| Chroma / adapter | Existing server 1.5.9; `langchain-chroma` 1.1.0 | Preserve policy collection and source/page IDs; align query embeddings explicitly. |
| Agent Server infrastructure | Validated pinned image; PostgreSQL 16.x and supported Redis image | Server-managed graph persistence and coordination, separate from booking SQLite. |
| Frontend / verification | Browser HTML/CSS/JS; pytest 9.2.0, HTTPX 0.28.1 | Simple chat, grid, table, and focused deterministic/integration checks. |

Resolve complete transitive dependencies rather than assuming table pins guarantee compatibility. Reproduce the reported NumPy/Chroma Python import failure in the selected runtime; HTTP heartbeat alone is insufficient. Verify Europe/Warsaw timezone data, including on Windows.

Standalone deployment has infrastructure credentials and possible license/egress requirements even though customers and administrators have no login or API keys. Current standalone prerequisites list LangSmith and license keys, PostgreSQL, and Redis; documentation examples are not fully consistent about entitlement. Build/start a pinned trivial graph and exercise an SDK thread/run early. A development server may aid diagnosis but does not prove the required final deployment.

The existing 1,536-dimensional vectors do not identify their embedding model. Recover ingestion provenance or explicitly plan a separately versioned collection rebuild; preserve the existing collection until retrieval checks pass. Do not issue speculative paid embedding calls or mix equal-dimension embedding spaces.

### Expected Features

See [FEATURES.md](FEATURES.md). All accepted table stakes and listed differentiators are required for this project's v1; generic marketplace priorities do not override its scope.

**Must have:**

- Customer chat with quick actions, a selected-interval slot grid, and a separate administrator bookings panel.
- Live SQL availability and PLN/hour pricing; supported date/type/slot validation and clear inventory coverage limits.
- Multi-turn collection of Name, Surname, Car Number, Zone/Slot, and Reservation Period, including corrections without losing prior details.
- Transactional `PENDING` holds, administrator confirmation/rejection, scoped cancellation, and refresh after committed mutations.
- Policy retrieval, structured evidence assessment, and an explicit no-available-information branch.
- Thread continuity, server-bound browser session association, bounded tools, safe customer projections, and input/output guardrails.
- SDK-backed REST integration and repeatable Compose setup with readiness and persistent storage.

**Required differentiators:**

- Dedicated vector and SQL nodes run in parallel for availability; policy-only questions use vector retrieval without waiting for an absent SQL branch.
- A custom query-indexed reducer preserves previous queries and merges current SQL/vector evidence idempotently despite completion order and retries.
- Historical evidence remains inspectable internally while every new availability question and booking write refreshes live SQL facts.
- Pending is visibly distinct from confirmed across SQL, chat, and grid; EV remains an attribute visible alongside interval status.

**Defer unless separately scoped:** payments, accounts/API-key authentication, public production exposure, automatic hold expiry, waitlists, cross-thread profiles, physical occupancy sensors, charging workflows, rich dashboards, and unlimited-date inventory. These are exclusions or potential future decisions, not promised v2 features.

Research recommendations still requiring phase-level decisions include half-open interval endpoints, same-day scope, legacy-status mapping, demo clock/past booking policy, plate normalization, slot-type matching, session lifetime, and grid defaults. SQL provides hourly rates; total-price rounding is not agreed. No automatic TTL is authorized.

### Architecture Approach

See [ARCHITECTURE.md](ARCHITECTURE.md). Keep a few explicit modules with small functions rather than generic agents or elaborate abstraction layers.

1. **Shared booking service:** deterministic validation, daily inventory identity, availability/pricing, lifecycle transitions, ownership, operation keys, and transactions. Both graph tools and REST routes call it.
2. **LangGraph workflow:** explicit input/output/main state, structured classifier/extractor/judge, separate retrieval nodes, reducer, controlled booking tools, response composition, and guards.
3. **FastAPI boundary:** browser-session/thread association, SDK calls, Pydantic contracts, safe customer outputs, separate administrator records, and error mapping.
4. **Persistence:** SQLite owns bookings; PostgreSQL owns Agent Server state; Chroma owns policy evidence; Redis supports runtime coordination.
5. **Simple frontend:** same-origin static chat, explicit interval selection, slot grid, and administrator table; mutation refresh plus modest polling/focus refresh across tabs.

**Patterns to adopt:**

- Mount the same local SQLite directory into graph and API, including journal/WAL sidecars; never ship independently writable database copies. Run one controlled migration before writers start.
- Preserve `(spot_id, slot_date)` identity. Compute interval availability from reservations and a shared blocking-status rule, never the November 9 snapshot flag.
- Use a short tested immediate-write transaction to validate/recheck/insert. Keep network/model calls outside it and bound busy handling.
- Persist operation identity before the side-effect node; uniquely store key, request fingerprint, and result atomically with the booking. Replay returns the original result; changed payload under the same key conflicts.
- Allocate a query index once per durable submission. Merge source results with stable identities; only current successful SQL evidence may support a live claim. Do not let branch updates replace draft/route fields.
- Serialize accepted turns per thread through Agent Server, preferably rejecting concurrent runs with a clear conflict response; independent threads remain concurrent.
- Inject trusted session ownership server-side. A supplied thread ID, reservation ID, or plate alone does not establish access. Restrict seeded ownerless records to administrator management unless explicitly designed otherwise.
- Finish after creating `PENDING`; admin PATCH updates SQL through conditional transitions. Reload owned reservation state on subsequent turns and API projections. Checkpoint status is a cache, not booking authority.

### Critical Pitfalls

See [PITFALLS.md](PITFALLS.md) for detailed scenarios and phase responsibilities.

| Risk | Prevention | Required evidence |
|------|------------|-------------------|
| Overlapping or duplicated bookings | Atomic conflict recheck/create; pending blocks; durable unique operation key | Two independent processes produce one overlapping hold; replay after commit produces one booking. |
| Fixture migration/time errors | Preserve records/keys; normalize instants; define status/date/working-hours rules | Original 1,440 slots and 720 reservations survive; November 11 create succeeds; unsupported December date is explicit. |
| Lost/stale evidence or mixed turns | Idempotent per-query reducer, current SQL selection, per-thread run policy | Both branch orders and retries preserve sources/history; changed interval triggers fresh SQL; concurrent same-thread turn is controlled. |
| PII disclosure or false administrator security | Ownership predicates, narrow tools/DTOs, output guard, internal graph services, trusted local bindings | Cross-session ID guessing fails; no unrelated names/plates in customer outputs/errors; effective ports remain local. |
| Green mocks hide unusable deployment/RAG | Early entitlement/import gates; embedding provenance; real Chroma and deployed SDK checks | Pinned image starts, thread survives restart, expected source/page retrieval works, live runs are reported accurately. |

## Implications for Roadmap

Use four standard-size phases built around usable outcomes. Verification belongs within every phase; do not create separate refactor or test-only phases.

### Phase 1: Reliable Booking and Runtime Foundation

**Rationale:** Every later answer and mutation depends on correct inventory/lifecycle rules and a deployable runtime. Discover entitlement or import failures before SDK application integration.
**Delivers:** Preserving migration, shared booking service, selected-interval availability/pricing, transactional pending/cancel/admin transitions, durable operation keys, and an early trivial deployed graph smoke gate.
**Addresses:** Validity, holds, approval/cancellation rules, current SQL truth, reproducible environment, shared storage, and deployment feasibility.
**Avoids:** Snapshot availability, status/date CHECK failures, double booking, retry duplicates, two SQLite copies, late entitlement discovery, and import-time fixture mutation.
**Acceptance:** Migrate a fixture copy and repeat safely; integrity/foreign keys and original keys/counts survive. Test adjacent/overlapping intervals, timezone-equivalent inputs, hours/date bounds, two-process conflicts, conditional decisions, and lost-ack replay. Build/start the pinned graph with readiness and SDK thread/run access; record model/embedding configuration gates without assuming account access.
**Planning decisions:** Canonical timestamps/statuses, historical blocking rules, half-open endpoints recommendation, same-day scope, clock policy, plate/type validation, cancellation ownership, and operation-key contract.

### Phase 2: Grounded Persistent Customer Conversation

**Rationale:** A deployed policy-answer slice proves graph state, retrieval, guardrails, and the real SDK transport before enabling conversational writes.
**Delivers:** Typed graph contracts, persistent thread state, structured intent/judge, query reducer, vector-only policy answers/no-information branch, session-bound FastAPI chat, and a minimal static chat with quick actions.
**Addresses:** Policy questions, thread continuity, safe customer replies, evidence retention, guardrails, and required deployed REST path.
**Avoids:** Wrong embedding space, unsupported policy claims, raw graph-state exposure, cross-session thread access, and in-process substitution for deployed chat.
**Acceptance:** Reviewed questions retrieve expected facility/source/page IDs; unsupported questions abstain; source/model failures remain distinct. Exercise real SDK runs and restart continuity; attempt cross-session thread access and injection through both user and retrieved text. Validate DTO/error boundaries and same-thread contention.
**Planning decisions:** Session lifetime/new-chat behavior, request retry identity, safe response schema, evidence outcome taxonomy, and initial reviewed retrieval dataset/thresholds.

### Phase 3: Live Availability Conversation and Slot Grid

**Rationale:** Extend the proven retrieval contract with parallel operational facts before introducing booking side effects through chat.
**Delivers:** Structured `check_availability` routing, dedicated parallel SQL/vector nodes and barrier, current-query judge rules, availability/pricing replies, `GET /api/slots`, and a simple interval-explicit grid with independent EV display.
**Addresses:** Accurate availability, hourly pricing, parallel retrieval, accumulated evidence history, coverage limits, and visual slot status.
**Avoids:** Policy-only barrier deadlocks, overwritten evidence, stale availability reuse, snapshot flags, and misleading green unsupported dates.
**Acceptance:** Run both branch completion orders, duplicate retrieval updates, and later queries; sources merge once and prior queries remain. Mutate SQL between turns and observe refreshed facts. Check unsupported inventory, fully blocked intervals, partial dependency failure, SQL/policy price conflict, and EV under every status.
**Planning decisions:** Grid default interval and status priority/legend, zone selection, exact type matching, partial-answer behavior, and refresh latency. Hourly pricing does not imply a billing or total-cost feature.

### Phase 4: Conversational Reservations and Administrator Approval

**Rationale:** Complete the core journey using the already tested booking service, deployed conversation, and live grid; SQL remains the common authority across all surfaces.
**Delivers:** Multi-turn booking draft/corrections, validated fixed tools, committed pending requests, customer cancellation, administrator GET/PATCH and table, SQL-based status reconciliation, cross-tab refresh, and repeatable local walkthrough.
**Addresses:** Full customer reservation journey, approval/rejection, hold release, safe booking projections, and integrated Compose acceptance.
**Avoids:** False confirmation, abandoned approval interrupts, resurrected cancellations, duplicate writes after transport failure, privacy leakage, and stale grid/chat status.
**Acceptance:** Through deployed API/UI collect missing fields, correct interval, submit once, observe pending hold, approve/reject, and query current status. Race two sessions for one interval, replay after commit/failed acknowledgement, and race cancellation with approval. Restart graph/API and verify one shared booking plus persistent conversation. Exercise actual Chroma/SDK, one dependency failure, session isolation, no-information behavior, and documented fresh-start setup.
**Planning decisions:** Idempotent repeated transitions, polling/focus refresh details, final safe booking fields, and error/recovery presentation. Keep pending until decision/cancellation; proactive notifications or automatic expiry require new scope.

### Phase Ordering Rationale

- Booking correctness and deployment feasibility are prerequisites, but application SDK integration waits until the graph image actually runs.
- The policy-chat slice exposes persistence, retrieval, privacy, and SDK transport issues without adding write ambiguity.
- Availability adds parallel state and current facts on that stable path; reservations then reuse the same facts and deterministic transactional service.
- Admin routes and conversational writes ship together so approval is demonstrable end to end; a pending SQL status does not require a suspended graph run.

### Research Flags

- **Phase 1: deeper research needed** for pinned Agent Server entitlement/configuration, dependency/import compatibility, preserving SQLite migration/transaction control, and embedding provenance recovery.
- **Phase 2: focused research needed** for pinned SDK run/retry semantics, session/thread integration, reducer identity, and real retrieval evaluation. Use official documentation, then execute smoke checks.
- **Phase 3: standard graph patterns once contracts are fixed**; targeted research only if pinned barrier/reducer APIs or partial-source behavior remain unclear.
- **Phase 4: standard booking/UI patterns using established service contracts**; research approval resume/outbox only if a new proactive-update requirement replaces refresh-on-next-turn. Do not introduce that mechanism by default.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Official model/PyPI/platform sources checked; full dependency lock, account access, image entitlement, and runtime imports untested. |
| Features | HIGH for agreed scope; LOW for external seam tier | PROJECT.md is authoritative. FEATURES.md conservatively labels fetched implementation evidence LOW; recommendations are not validated market demand. |
| Architecture | MEDIUM | Official framework patterns support the design; cross-service consistency and deployed integration remain proposals. |
| Pitfalls | HIGH for observed constraints/documented mechanisms; MEDIUM for mitigations | Fixture restrictions and replay/concurrency risks are grounded; proposed prevention needs executable acceptance evidence. |

**Overall confidence:** MEDIUM. Report-specific confidence methods differ; source quality is not proof that this implementation works. No live model call, paid embedding operation, server entitlement check, or application concurrency test was performed by this synthesis.

### Gaps to Address

- **Access and deployment:** Public model ID is established, account entitlement is not. Verify exact model access/structured output and pinned Agent Server licensing/configuration; never silently swap model or architecture.
- **Existing embeddings:** Recover model/provenance; otherwise plan a controlled versioned rebuild and reviewed retrieval comparison without destroying the original corpus.
- **Business semantics:** Assign interval, timezone, legacy history, past-time, plate/type, slot selection, and session choices to the phases above. November policy/inventory coverage is finite.
- **Cross-service persistence:** Exercise real two-container local SQLite locking, permissions, sidecars, and crash recovery. This topology is single-host, not a multi-host scaling plan.
- **Evidence quality:** Establish reviewed questions across all facilities and unsupported cases before tuning. Measure retrieval relevance, factual correctness, groundedness, and question relevance separately; do not use the runtime judge as sole evaluator.
- **Acceptance reporting:** Keep deterministic default tests separate from configured live-model/deployed evaluation; skipped live checks remain unverified. Inject a clock and failure points rather than relying on real dates or lucky scheduling.

## Sources

### Project Authority and Detailed Research

- [PROJECT.md](../PROJECT.md): accepted scope, fixture inspection, trust boundary, exclusions, and open semantics.
- [STACK.md](STACK.md), [FEATURES.md](FEATURES.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PITFALLS.md](PITFALLS.md): full findings and source-specific confidence, accessed/researched 2026-11-10.
- [Codebase concerns](../codebase/CONCERNS.md), [seed database](../../ingested_mock_data/seed_database.py), [vector ingestion](../../ingested_mock_data/seed_vector_ingest.py): migration restrictions, import side effects, and missing embedding identity, as inspected by researchers.

### Primary External Sources

- [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-6-luna), [changelog](https://developers.openai.com/api/docs/changelog), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs): public model identifier and schema support; account access not established.
- [LangChain PyPI](https://pypi.org/pypi/langchain/json), [LangGraph PyPI](https://pypi.org/pypi/langgraph/json), [SDK PyPI](https://pypi.org/pypi/langgraph-sdk/json): candidate versions and declared compatibility; remaining package sources are in STACK.md.
- [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), [persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance): reducers, thread state, retries, and external side-effect responsibility.
- [Standalone Agent Server](https://docs.langchain.com/langsmith/deploy-standalone-server), [CLI](https://docs.langchain.com/langsmith/cli), [application structure](https://docs.langchain.com/langsmith/application-structure): image, configuration, service, and credential prerequisites.
- [Reject concurrent runs](https://docs.langchain.com/langsmith/reject-concurrent): per-thread run rejection; validate against pinned server/SDK.
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html), [isolation](https://www.sqlite.org/isolation.html), [WAL](https://www.sqlite.org/wal.html), [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/21/dialects/sqlite.html): writer coordination, transaction behavior, and local shared-file limitations.
- [Chroma collection configuration](https://docs.trychroma.com/docs/collections/configure), [embedding functions](https://docs.trychroma.com/docs/embeddings/embedding-functions): explicit embedding setup; no proof of historical collection identity.
- [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/), [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/): projections and readiness dependencies.
- [OWASP prompt injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), [RAG evaluation tutorial](https://docs.langchain.com/langsmith/evaluate-rag-tutorial): layered boundaries and distinct evaluation dimensions.

---
*Research completed: 2026-11-10*
*Ready for roadmap: yes; runtime and product-semantic gates remain explicit acceptance work.*

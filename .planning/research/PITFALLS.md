# Domain Pitfalls

**Project:** Parking Reservation Assistant
**Domain:** Local conversational parking allocation with administrator approval
**Researched:** 2026-11-10, Europe/Warsaw
**Confidence:** HIGH for inspected fixture constraints and documented platform behavior; MEDIUM for proposed designs until exercised against the pinned deployment.

## Research Basis

This document combines direct inspection of `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`, `ingested_mock_data/seed_database.py`, and `ingested_mock_data/seed_vector_ingest.py` with current official SQLite, LangChain/LangGraph, Chroma, FastAPI, and OWASP documentation. Links accompany relevant claims. Recommendations and regression scenarios are project-specific engineering inferences, not claims that the planned application already implements them. The supplied SQLite artifact is reported healthy; these are risks of evolving it into a reservation service, not evidence of existing corruption.

No configured researcher skills were returned by the local bootstrap. Primary documentation was read directly; optional provider/cache/confidence seams were not used. Confidence labels below describe evidence strength rather than a CLI-generated classification. No model, server entitlement, embedding identity, or end-to-end application behavior was verified by running services during this bounded research.

Phase names below indicate responsibilities rather than fixed roadmap numbers.

## Critical Pitfalls

### 1. Treating an availability lookup as a reservation lock

**What goes wrong:** Two customers both see a free interval and create overlapping reservations. Ignoring `PENDING` lets another customer reserve an interval awaiting approval. Updating a daily availability flag cannot express multiple partial-day visits.

**Why it happens:** The seed generates non-overlapping data but its schema does not enforce interval exclusion. SQLite has a single writer, but a separate read followed later by a write does not establish the desired business invariant. SQLite documents that `BEGIN IMMEDIATE` acquires a write transaction immediately and can return `SQLITE_BUSY` when another writer holds it. [SQLite transactions](https://www.sqlite.org/lang_transaction.html).

**Prevention:** Put normalized input validation, authoritative overlap recheck, and insertion in one short ORM-backed transaction using an explicitly tested immediate-write strategy. Use half-open intervals: an existing booking overlaps when `existing.start < requested.end AND existing.end > requested.start`. Establish one blocking-status mapping including new `PENDING` and legacy `confirmed`/`active`; normalize casing at the boundary. Reject past bookings separately rather than inferring time from stale fixture statuses. Use bounded busy handling that retries the whole allocation transaction, never only the insert. Enable foreign keys on every connection. Never hold a transaction open across an LLM call. Graph tools and administrator routes must call the same booking service.

**Warning signs:** Tests cover only sequential inserts; availability uses `current_availability`; `SELECT` and `INSERT` occur in different sessions; the API and graph define different blocking statuses.

**Regression checks:** Launch two independent connections/processes against the same temporary file and synchronize competing requests: exactly one overlapping hold succeeds, the other returns a domain conflict. Cover identical, containing, contained, partially overlapping, and adjacent intervals; different spots; pending/confirmed holds; released cancelled holds; busy timeout; foreign-key rejection. Test real file-backed SQLite rather than isolated per-connection in-memory databases.

**Phase responsibility:** Booking data foundation, before graph writes or administrator mutations. **Confidence:** HIGH for SQLite semantics and current missing constraint; MEDIUM for the proposed ORM transaction implementation until contention tests pass.

### 2. Adding `PENDING` without migrating the fixture or defining transitions

**What goes wrong:** A correct-looking booking tool fails its first insert because the existing status CHECK excludes `PENDING`. Bookings after November 10 fail even though daily inventory extends to November 30. A rerun of `CREATE TABLE IF NOT EXISTS` does not alter either restriction. A late administrator approval can also revive a cancelled request if updates are unconditional.

**Prevention:** Make an explicit, preserving schema migration with backup and pre/post integrity checks; map legacy lowercase values deliberately. Define allowed transitions: `PENDING -> CONFIRMED` and `PENDING -> CANCELLED`, plus scoped customer cancellation for supported cancellable states. Define repeated decisions as idempotent or explicit conflicts. Use conditional status updates so competing approval/cancellation decisions cannot silently overwrite each other. Cancellation/rejection releases the interval through the blocking-status rule. Do not add automatic hold expiry without a product decision: current scope keeps holds until decision or cancellation. Approving an already held interval must preserve the allocation invariant; do not let a generic PATCH change spot/time or revive a terminal record.

**Warning signs:** Migration is described as rerunning the seed; uppercase API statuses are inserted into the legacy table unchanged; administrators can PATCH any row into any status; the chat says confirmed after creating a pending request.

**Regression checks:** Migrate a copy of the original artifact and preserve its 1,440 slot and 720 reservation records and keys. Verify integrity/foreign keys, a November 11 pending insert, repeat migration, cancellation followed by approval, duplicate approval, conflicting administrator decisions, and immediate release after rejection. Ensure no hidden expiry job exists.

**Phase responsibility:** Schema/lifecycle foundation; reuse in booking graph and administrator API phases. **Confidence:** HIGH from the inspected SQL CHECK clauses and agreed requirements; transition handling is a recommended design.

### 3. Comparing timestamps as arbitrary strings or promising dates outside inventory

**What goes wrong:** Text ordering mistakes `T` versus space, differing offsets, or different precision for chronological order. A request crosses a local day yet is assigned one daily slot. Fixed UTC+01:00 is incorrectly reused beyond this November fixture. The grid labels an unsupported date free because it found no reservations.

**Why it happens:** Seed values use space-separated, offset-aware strings and same-day substring CHECKs. Reservations currently permit November 1–10; slots permit November 1–30; `current_availability` is November 9 noon. SQLite date functions normalize recognized offsets, which is different from comparing original TEXT values. [SQLite date/time functions](https://www.sqlite.org/lang_datefunc.html).

**Prevention:** Define Europe/Warsaw parsing and local-business-day semantics before migration. Normalize all comparisons to one representation, preferably integer UTC instants plus an explicit local slot date; preserve each existing instant during conversion. Use a named timezone for business hours. Retain same-day booking as an explicit v1 rule unless a separate cross-day allocation design is chosen. Enforce start < end, supported inventory date, local 06:00–22:00, slot/type existence, and the chosen past-time policy deterministically. Distinguish no matching inventory from an interval fully booked. Migration beyond November 10 does not itself create inventory beyond November 30.

**Warning signs:** Direct comparison of incoming ISO strings to seed text; implicit machine-local timezone; missing slots treated as zero occupancy; actual system time baked into tests.

**Regression checks:** Equivalent instants expressed as UTC/+01:00, `T`/space input, precision differences, reversed/equal intervals, midnight crossing, 06:00/22:00 edges, November 10/11/30 and December 1. Use an injected clock. If accepting dates outside this fixture later, add DST ambiguous/nonexistent-local-time tests before expanding coverage.

**Phase responsibility:** Domain/schema foundation; frontend interval selection must reuse this contract. **Confidence:** HIGH for fixture constraints and documented date handling; MEDIUM for final storage choice pending phase design.

### 4. Assuming graph checkpointing makes external booking writes exactly once

**What goes wrong:** SQLite commits a hold, the graph loses its acknowledgement/checkpoint, and retry creates another booking. A timeout is reported as failure even though the booking exists. Replaying a cancellation or administrator resume has an unintended second effect.

**Why it happens:** Graph retries restart the node; external effects are outside the graph-state checkpoint boundary. Official guidance requires stable idempotency identities and treats missing acknowledgement as an unknown outcome. [LangGraph fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance).

**Prevention:** Persist a logical booking-operation identity before the writing node, or derive it from already durable state. Enforce uniqueness in SQLite and atomically store the operation and its result with the reservation. On replay return the original result; reject reuse of a key with different normalized details. Preserve the same operation identity for HTTP request retries as well as node retries. Distinguish user intent to make another booking from transport retry. Retrieve the recorded result after an uncertain timeout before declaring success/failure. Repeated status changes must follow the same idempotency and transition rules.

**Warning signs:** A UUID is generated inside the writing node; retry tests raise only before commit; request retries allocate a fresh reservation ID; graph rollback is assumed to undo SQLite.

**Regression checks:** Inject failure immediately after SQLite commit and before graph return/checkpoint, then resume/retry in a fresh process. Assert one booking, one hold, stable ID/result. Repeat a client request; change details under the same key; test cancellation and administrator status synchronization after interrupted runs.

**Phase responsibility:** Booking service and graph persistence integration, before enabling retries or human approval resumes. **Confidence:** HIGH for replay semantics; MEDIUM for proposed application deduplication until crash tests pass.

### 5. Losing evidence during parallel retrieval or concurrent turns

**What goes wrong:** Vector and SQL nodes write the same field and overwrite or conflict; a new message clears old evidence; retries append duplicates. Two turns allocate the same query index or mix booking details. A reducer retaining history does not itself serialize thread execution.

**Prevention:** Specify a typed map keyed by durable per-query identity/index; each entry has separate vector and SQL subrecords, stable evidence IDs, retrieval timestamp, normalized query/interval, and explicit source outcome. A custom reducer must merge only changed entries, preserve older queries, and deduplicate repeated node output. Define deterministic behavior for repeated writes to the same source entry. Join the required retrieval branches before judging that query. Test state contracts independently from prompting. LangGraph documents reducers, concurrent super-steps, and node re-execution in its [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api).

**Concurrent turns:** Explicitly select and verify Agent Server `enqueue` behavior for the pinned version, or reject overlapping requests with a clear retry response. Do not rely only on a disabled frontend button. Current docs describe enqueue as the default and distinguish server multitasking from OSS graph behavior. Avoid interrupt/rollback for booking requests unless external SQLite effects are reconciled. [Agent Server double texting](https://docs.langchain.com/langsmith/double-texting).

**Warning signs:** All evidence shares one list with ordinary append; query counter increments independently in each branch; tests assume SQL always finishes first; API invokes the same thread concurrently without a policy.

**Regression checks:** Deliver SQL/vector updates in both orders and repeat them; assert one equivalent merged result and previous-query retention. Exercise empty/failing branches and checkpoint reload. Send two simultaneous messages to one thread and to distinct threads: verify correct order, distinct query identities, no cross-thread evidence or booking details, and one judge invocation per completed query.

**Phase responsibility:** Graph state/retrieval phase; recheck through deployed SDK/API integration. **Confidence:** HIGH for documented state/concurrency mechanisms; MEDIUM for the recommended reducer algebra and query identity design until implemented.

### 6. Letting preserved historical SQL become current evidence

**What goes wrong:** The assistant correctly remembers yesterday's availability but presents it as current; the judge accepts evidence for another date/spot; a grid still shows free after a pending hold. Source citations can look convincing while being irrelevant to the requested interval.

**Prevention:** Preserve historical evidence for continuity, but select the current query's evidence for answering. Re-query SQL for each new availability question and inside every allocation transaction. Include normalized interval/date, retrieval time, and source in evidence. SQL governs live inventory/pricing; policy PDFs govern documented rules and effective coverage. A query-time freshness check is a routing rule, not an LLM opinion. Refresh the grid from persisted SQL after booking/cancellation/administrator updates; retain EV/type badges alongside occupancy state.

**Warning signs:** Judge sees the complete evidence archive without query selection; remembered availability bypasses SQL; frontend mutates only a local cell; pricing silently follows an older PDF over SQL.

**Regression checks:** Ask availability, book via another session/admin path, then ask again in the original thread. Confirm fresh SQL and changed answer/grid while old evidence remains stored. Test same wording for another interval, adjacent slots, an EV pending hold, and a policy/live-price discrepancy with explicit source precedence.

**Phase responsibility:** Retrieval/evidence contract, transactional booking, and frontend synchronization phases. **Confidence:** HIGH for project requirements and snapshot limitations; recommendations are project-specific freshness controls.

### 7. Making the evidence judge or injection filter the security boundary

**What goes wrong:** A malicious message or retrieved page asks for another customer's plate, arbitrary SQL, or administrative approval. A structured judge can still confidently approve unsupported text. Removing a few patterns or filtering the final answer cannot undo excessive tool access.

**Prevention:** Keep the requested input filter, structured sufficiency judge, and outgoing guardrail, but enforce parameterized fixed-purpose tools, allowed operations/statuses, session-scoped reservation queries, and field allowlists in code. Availability tools return spot/type/price/interval status, not customer rows. Bind the browser session to allowed thread/reservation references on the server; a supplied `thread_id`, reservation ID, or car number alone must not confer access. A plate comparison is an extra cancellation condition, not identity proof. Do not place other customers' PII in model context or return raw checkpoint/tool state. Use separate explicit customer/admin response schemas; FastAPI supports output filtering through response models. [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/).

**Evidence:** OWASP recommends session-aware tool permission/parameter checks and least privilege, and states model-based guardrails are another layer rather than an authorization mechanism. [OWASP prompt injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

**Warning signs:** Model generates SQL; `SELECT *` reaches prompts; response is an unfiltered state dictionary; a keyword blacklist is described as sufficient protection; logs include full customer prompts/tool rows by default.

**Regression checks:** Inject instructions in user text and a retrieved page; ask for all bookings/plates, bypass approval, execute SQL, or disclose checkpoint history. Swap session/thread/reservation identifiers across browsers and try cancellation with a known plate. Assert no forbidden tool operation and no cross-customer fields in success/error/stream responses or ordinary logs, regardless of whether the model follows the injection. Add benign plate/name questions to track overblocking.

**Phase responsibility:** Data/tool boundaries before model integration; session projection in API phase; adversarial checks throughout graph evaluation. **Confidence:** HIGH for documented control principles; no claim that any prompt/guardrail guarantees injection resistance.

### 8. Mistaking separate administrator routes for access control

**What goes wrong:** The local trusted demo is exposed on a LAN/public interface and anyone can list customer records or approve bookings. CORS is treated as authentication. Conversely, implementation adds accounts/API keys despite the agreed local scope.

**Prevention:** Preserve the agreed no-login/no-API-key application model and document its actual boundary: any actor with local trusted access to the admin surface can administer records. Publish customer/admin application ports only on intended loopback interfaces; keep Agent Server, SQLite, Chroma, PostgreSQL, and Redis access internal where practical. Use explicit browser origins and request origin/CSRF defenses appropriate to no-auth browser mutations; CORS alone does not establish administrator identity. Browser session association reduces accidental cross-session disclosure but is not a hostile multi-user authentication design. Widening deployment exposure is a new design decision, not a routing change.

**Warning signs:** Compose publishes `0.0.0.0` by convenience; README calls `/api/reservations` protected solely because it is in the admin panel; a customer thread identifier is forwarded directly to arbitrary graph threads.

**Regression checks:** Review effective Compose bindings and accessible ports. Confirm cross-origin mutation behavior, safe customer projections, and session/thread binding. Verify UI separation without claiming it secures admin endpoints against trusted local actors. Do not add authentication deliverables to satisfy this check.

**Phase responsibility:** Deployment/API boundary; document in local setup and demo acceptance. **Confidence:** HIGH for the explicitly agreed trust model; specific network/origin implementation remains MEDIUM until exercised.

### 9. Shipping two independent booking databases or discovering deployment entitlement last

**What goes wrong:** The graph writes its image's SQLite copy while FastAPI reads another; administrator decisions appear ineffective and grid/chat disagree. A container restart loses bookings. The final deployment fails because platform credentials/licensing requirements were assumed away.

**Prevention:** Mount one local booking-data directory into both graph and API and configure one canonical file path. Mount the directory rather than only the file so SQLite journal/WAL sidecars share the same local filesystem. Initialize/migrate through a single controlled operation before writers start; never auto-seed over customer data on service startup. Use PostgreSQL for graph persistence and SQLite for bookings as required. Verify both services share schema/version/transaction rules and file identity. Keep transactions short and handle contention; do not scale this local shared-file topology into arbitrary hosts.

**Deployment gate:** Current standalone documentation specifies PostgreSQL/Redis and lists `LANGSMITH_API_KEY` and `LANGGRAPH_CLOUD_LICENSE_KEY`, including startup license validation. Perform an early pinned-image build/start/SDK thread-run smoke test with available entitlement, service readiness, and container addresses. Surface unavailable requirements explicitly; do not silently replace Agent Server or introduce another agent framework. Application no-auth scope does not remove infrastructure/provider credential requirements. [Standalone Agent Servers](https://docs.langchain.com/langsmith/deploy-standalone-server).

**Warning signs:** Each Dockerfile copies a writable SQLite artifact; API queries show unchanged seed counts after graph writes; setup has only process-start dependencies; a successful in-process graph invocation is called a deployed integration test.

**Regression checks:** Through deployed SDK create a pending booking, read it through admin API and slots, change status, and query chat again. Restart both services and verify consistency plus graph checkpoint persistence. Stop Chroma/PostgreSQL/Redis and inspect readiness/error recovery. Confirm a fresh checkout can follow documented pinned build/start steps without hidden local state or committed credentials.

**Phase responsibility:** Deployment feasibility smoke test early; shared storage before booking integration; full deployment before SDK-backed API acceptance. **Confidence:** HIGH for documented prerequisites and project deployment shape; actual entitlement and pinned-image compatibility remain unverified gates.

## Moderate Pitfalls

### 10. Confusing insufficient evidence, no availability, and service failure

**What goes wrong:** A Chroma timeout becomes “there is no information,” a SQLite lock becomes “fully booked,” or an invalid judge response becomes an affirmative answer. The result hides an operational fault as domain truth.

**Prevention:** Give retrieval outcomes typed distinctions: success with evidence, success with zero relevant records, unsupported inventory/date, and dependency/error outcomes. Judge sufficiency only after required sources succeed; distinguish no free interval from no policy evidence. Apply bounded retries to transient infrastructure errors, validation/conflict messages to domain failures, and clear temporary-unavailability responses to exhausted dependencies. A judge schema enforces format, not factual truth. Do not expose stack traces or customer data in error bodies.

**Warning signs:** Broad `except Exception: return []`; one “no information” branch handles all failures; HTTP 200 always means success; absence of SQL rows is interpreted without checking inventory.

**Regression checks:** Independently inject empty retrieval, irrelevant policy, no matching slots, all slots blocked, source timeout, SQLite busy exhaustion, and malformed judge output. Verify distinct safe outcomes, preserved source error metadata, and no write following failed validation/retrieval.

**Phase responsibility:** Evidence/judge design and API error mapping. **Confidence:** MEDIUM; recommended project outcome taxonomy, informed by documented graph error handling and the explicit no-information requirement.

### 11. Guessing the embedding model from 1,536 dimensions

**What goes wrong:** New query vectors have the right length but come from a different embedding space, degrading retrieval without an obvious dimension error. A collection containing 36 IDs is called accurate even when its source text/configuration is stale.

**Prevention:** The inspected ingest script leaves `OpenAIEmbeddings` at its default; project inspection found no recorded model identity. Treat identity as unknown until provenance/configuration establishes it. Record model/provider, dimensions, relevant parameters, dependency versions, source/page IDs, and content hashes for repeatable ingestion/querying. Current Chroma docs describe persisted embedding-function configuration, but that does not establish the provenance of this existing LangChain-managed collection. If identity cannot be recovered, propose a controlled rebuild into a separately named/versioned collection with explicit configuration and validate retrieval before switching. Do not destroy the existing collection speculatively. [Chroma collection configuration](https://docs.trychroma.com/docs/collections/configure).

**Warning signs:** “1536 means model X”; defaults differ between ingestion and query code; ingestion checks only ID count; renamed/deleted PDFs leave old pages retrievable.

**Regression checks:** A fixed representative question set must retrieve expected facility/source/page IDs and relevant policy text from the actual collection. Detect wrong embedding identity even when dimensions match. Check current source hashes, removed/renamed pages, empty pages, and collection/configuration mismatch before deployment.

**Phase responsibility:** Environment/retrieval foundation, before tuning the judge or claiming RAG accuracy. **Confidence:** HIGH for observed missing provenance; MEDIUM for recovery until original embedding identity is established.

### 12. Imports mutate fixtures, and health checks miss the broken Python client

**What goes wrong:** Test collection imports a seed module and writes the real SQLite file, overwrites PDFs, or makes paid embedding calls. HTTP Chroma heartbeat works while application imports fail due to the reported NumPy C-extension issue. Re-running the seed is incorrectly used as a schema migration.

**Prevention:** Introduce explicit script entry points before reusing helpers. Isolate pure fixture builders and inject output paths/clients; use a local random generator. Preserve existing seed rerun semantics instead of silently refreshing records. Establish a reproducible locked Python environment and an actual application import + Chroma client/query smoke test. Diagnose the local NumPy failure from the runtime traceback; its cause has not been established by the codebase inspection. Do not paper over it with an undocumented package substitution or assume direct HTTP success proves the application path works.

**Warning signs:** Tests import scripts directly; CI needs provider credentials for unit test discovery; test runs alter real fixture timestamps; Docker health is green but `import chromadb` fails.

**Regression checks:** Import reusable modules with network calls blocked and outputs redirected to a temporary directory: no files change and no client calls occur. In the pinned app container, import dependencies, call Chroma heartbeat, load the collection and run one retrieval. Validate schema separately from seed row existence.

**Phase responsibility:** Environment and fixture safety first; retrieval container smoke test before graph integration. **Confidence:** HIGH for inspected import-time effects; MEDIUM for NumPy diagnosis, since only the prior failure report is available.

### 13. Declaring RAG and REST integration complete using mocks alone

**What goes wrong:** Mocked retrievers guarantee the right page and mocked judges guarantee approval, masking wrong embeddings, retrieval misses, and unsupported answers. FastAPI tests mock `langgraph_sdk` and never detect wrong graph IDs, deployment schemas, persistence, or transport behavior.

**Prevention:** Keep deterministic tests for reducers, tools, routes, and errors, then add a separately configured integration/evaluation suite against actual Chroma and the deployed Agent Server via `langgraph_sdk`. Use representative questions with expected facility/source/page and factual answer checks, plus unsupported-date, no-information, stale-availability, and injection cases. Separate retrieval relevance, answer correctness, groundedness, and question relevance rather than asking one judge whether everything is good. These dimensions are distinguished in the official [RAG evaluation tutorial](https://docs.langchain.com/langsmith/evaluate-rag-tutorial). Calibrate judge decisions against reviewed examples; do not use the same runtime sufficiency decision as independent proof of accuracy. Label paid/live-model runs explicitly and report skipped runs as unverified.

**Warning signs:** All retrieval tests replace the vector store; live tests assert only nonempty text; the deployed chat path invokes an in-process graph; only a happy-path request is exercised.

**Regression checks:** Run a small reviewed corpus covering all four facilities, hours/pricing/types and unavailable information. Assert expected sources and deterministic SQL facts, not exact prose. Through deployed API exercise multi-turn slot filling, same-thread retention, cross-thread separation, pending creation, administrator cancellation, safe response projections, restart/resume and one injected dependency failure. Record model/configuration/dataset versions and measured results without inventing an accuracy threshold after seeing scores.

**Phase responsibility:** Evaluation dataset starts with retrieval; API deployment integration and final demo verification complete it. **Confidence:** HIGH for evaluation distinctions; MEDIUM for final acceptance thresholds pending agreed dataset and observed baseline.

## Pitfall-to-Phase Mapping

| Phase responsibility | Pitfalls | Exit evidence |
|---|---|---|
| Environment/deployment feasibility | 9, 11, 12 | Reproducible dependency imports, Chroma query, explicit embedding provenance plan, pinned server entitlement/start/SDK smoke test. |
| Schema/domain booking foundation | 1, 2, 3, 4 | Preserving migration, canonical interval/status contract, concurrency and crash-idempotency checks. |
| Graph state/retrieval/judge | 4, 5, 6, 7, 10, 13 | Reducer/order/retry retention, source outcomes, fresh SQL selection, reviewed retrieval baseline, no arbitrary tools. |
| Reservation conversation/approval | 1, 2, 4, 7 | Multi-turn detail retention, one pending hold, controlled cancellation/decision, resumed state reconciled with SQLite. |
| Deployed SDK-backed FastAPI | 5, 7, 8, 9, 10, 13 | Session/thread binding, safe projections, status/error contracts, shared SQLite, real SDK calls and same-thread concurrency policy. |
| Simple UI and integrated verification | 6, 8, 9, 13 | Interval-explicit grid, separate EV/status display, refresh after both mutation paths, complete deployed customer/admin flow. |

## Sources

Official pages were accessed on 2026-11-10. They are living documentation; claims about the pinned implementation still require execution checks.

- [SQLite transaction behavior](https://www.sqlite.org/lang_transaction.html) — HIGH: immediate transactions, writer contention, snapshot behavior.
- [SQLite date/time functions](https://www.sqlite.org/lang_datefunc.html) — HIGH: accepted timestamp/offset normalization; project-specific storage choice remains a recommendation.
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) — HIGH: state, reducers, super-steps and re-execution.
- [LangGraph fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance) — HIGH: node retries, external effects, stable idempotency identities and uncertain acknowledgement.
- [Agent Server double texting](https://docs.langchain.com/langsmith/double-texting) — HIGH: concurrency strategies and documented enqueue default.
- [Standalone Agent Server deployment](https://docs.langchain.com/langsmith/deploy-standalone-server) — HIGH: documented services and license/key configuration; account/image entitlement not tested.
- [OWASP prompt injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) — HIGH: authoritative defensive guidance; not empirical proof of this application's resistance.
- [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/) — HIGH: response validation/projection mechanism; models must still be designed correctly.
- [Chroma collection configuration](https://docs.trychroma.com/docs/collections/configure) — HIGH: current embedding configuration features; existing collection provenance remains unresolved.
- [LangChain RAG evaluation tutorial](https://docs.langchain.com/langsmith/evaluate-rag-tutorial) — HIGH: evaluation dimensions; project dataset/thresholds remain to be established.
- Local primary evidence: `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`, `ingested_mock_data/seed_database.py`, `ingested_mock_data/seed_vector_ingest.py` — HIGH for directly inspected code/requirements; prior runtime findings are reported as such rather than reproduced.

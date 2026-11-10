# Feature Research

**Domain:** Local conversational parking reservation demo with customer chat, interval slot grid, and administrator approval panel
**Project:** Parking Reservation Assistant
**Researched:** 2026-11-10, Europe/Warsaw
**Research confidence:** LOW under the configured confidence seam; explicit project requirements below remain the accepted scope, not speculative market findings.

## Scope and Evidence

Build a complete local booking journey against the existing SQLite inventory and Chroma policy corpus. The useful differentiator is a conversation that remembers booking details while keeping live SQL facts, policy evidence, and administrator decisions consistent. A broad parking marketplace comparison would introduce requirements that do not belong in this demo.

The local sources are [PROJECT.md](../PROJECT.md), [codebase architecture](../codebase/ARCHITECTURE.md), and [fixture README](../../ingested_mock_data/README.md). They establish 48 physical spots, 1,440 daily inventory rows for November 1–30, 2026, 720 seeded reservations for November 1–10, and policies effective during November 2026. The November 9 noon availability flag is a historical snapshot. It cannot establish availability for a requested interval.

External documentation was fetched directly from primary sources on the research date. Context7 tools and the `ctx7` CLI were unavailable. The research-plan seam selected Context7, so the fallback was official web documentation. `classify-confidence --provider webfetch --verified` returned LOW; this conservative machine tier is retained for externally researched implementation claims. Complexity, ordering, and recommended behaviors are analysis for planning, not measured customer demand. No competitor or popularity claims are made.

## Feature Landscape

### Table Stakes: Required for This v1

All rows are required by the accepted project scope. Complexity is relative to this repository, whose application source is currently empty.

| Feature | Why Expected | Complexity | Required Behavior |
|---------|--------------|------------|-------------------|
| Customer chat and quick actions | Customers need an entry point for questions, availability, booking, and cancellation | MEDIUM | Show assistant replies, missing details, validation errors, and persisted booking outcomes; quick actions submit the same supported intents as typed text. |
| Availability and hourly pricing | A valid booking starts with a real interval and inventory record | HIGH | Ask for missing interval/type/facility details; read SQL for current facts; show PLN/hour from matching daily inventory. Do not invent prices or availability from PDF text. |
| Multi-turn booking collection | Customers rarely give every field in the first message | HIGH | Collect Name, Surname, Car Number, Zone/Slot, and Reservation Period; preserve prior fields; incorporate corrections; ask only for missing or invalid information. |
| Deterministic validation | Fluent text must not create invalid reservations | HIGH | Validate plate format, start before end, timezone, daily inventory identity, supported slot type, working hours, and blocking overlaps. Return actionable field-level problems. |
| Transactional request and hold | Two customers must not obtain overlapping claims | HIGH | Recheck inside the write transaction; insert one `PENDING` reservation and hold its interval; report submission only after commit. Graph retries and duplicate submissions must not create duplicate rows. |
| Administrator inspect/approve/reject | Approval is central to the requested lifecycle | MEDIUM | Separate panel lists reservation records; approve a pending request as `CONFIRMED`; reject it as `CANCELLED`; release rejected holds after commit. Invalid or racing transitions return an explicit result. |
| Customer cancellation | Customers need to release their reservation | MEDIUM | Check reservation ID and normalized plate plus the agreed session ownership scope; apply a controlled status update and release its hold. Do not disclose another customer's booking to explain a mismatch. |
| Slot grid with interval context | A visual result must agree with the conversational result | MEDIUM | Display the chosen date/start/end and status derived from SQL; show EV capability independently; refresh after booking, cancellation, and administrator decisions. |
| Thread continuity and session isolation | Details from one conversation must not leak into another | HIGH | Maintain conversation/booking state within its thread and bind thread access to its browser session. Merely knowing a thread ID must not grant access. |
| Policy answers and grounded abstention | Customers need supported facility rules and honest limits | HIGH | Retrieve policy pages, assess evidence with structured output, answer within source scope, and return no-available-information when evidence is insufficient. |
| Customer/admin response boundaries | The admin list contains data the customer grid must never contain | HIGH | Separate safe response schemas; narrow SQL results before generation; guard outgoing text; exclude unrelated names, plates, reservation records, internal prompts, and raw graph state. |
| Clear failures and recovery | Retrieval or write failures must not look like business facts | MEDIUM | Distinguish no supporting evidence, no free slots, invalid inputs, service errors, and an uncertain write acknowledgement. Preserve the booking draft when a recoverable operation fails. |

### Differentiators: Valuable and Already Required

These distinguish this assistant from a simple booking form. They are mandatory project requirements even though they would be optional in a generic parking MVP.

| Feature | Value Proposition | Complexity | Scope Boundary |
|---------|-------------------|------------|----------------|
| SQL facts plus vector policies | Combines operational truth with explanations | HIGH | Policy/general intent uses the vector node; availability/pricing intent uses dedicated SQL and vector nodes in parallel with a join and evidence assessment. SQL remains authoritative for availability/pricing. |
| Query-indexed evidence history | Prior answers remain inspectable without losing parallel updates | HIGH | Custom reducer merges SQL and vector evidence for the same query, preserves prior query entries, and deduplicates retries using stable identities. Historical SQL evidence does not become fresh availability. |
| Stateful field collection | Makes a partial request usable across turns | HIGH | Names, plate, slot, and interval persist within the thread; a changed interval invalidates its previous availability check. Do not add cross-session profiles. |
| Honest pending state across chat and grid | Customers understand that requesting is different from approval | HIGH | A committed pending request blocks competing requests and is visibly awaiting approval; only a persisted administrator decision may produce a confirmed result. |
| Grounded no-information path | Prevents plausible invented policies | MEDIUM | Use a structured evidence judge and conditional branch. A transport exception is a service failure, not evidence that information does not exist. |
| Deployed graph behind a simple API | Exercises the requested runtime rather than a local-only prototype | HIGH | Package the graph server first; the FastAPI chat path uses `langgraph_sdk`; return only the approved customer projection. No extra orchestration framework. |

LangGraph documents thread-scoped checkpoint state and separate cross-thread stores; its reducer contract requires explicit merge logic for fields that accumulate evidence. These support the memory design, while browser ownership remains an application responsibility. See [persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [state reducers](https://docs.langchain.com/oss/python/langgraph/graph-api-state). **External confidence: LOW per seam; validate against pinned versions.**

### Anti-Features: Explicitly Exclude

| Feature | Why It Looks Attractive | Why Avoid in This Scope | Use Instead |
|---------|-------------------------|-------------------------|-------------|
| Customer/admin accounts, login, or API keys | Familiar identity and privilege model | Explicitly excluded for this trusted local demo | Separate surfaces/routes and server-enforced customer session association; document the local boundary. |
| Payments, deposits, refunds | Common in commercial parking | Adds a separate financial lifecycle absent from requirements | Grounded hourly pricing information. |
| Public production exposure | Easy sharing | Separate routes do not establish administrator authorization | Keep deployment within the agreed local trusted environment. |
| More agent frameworks or autonomous SQL agents | Fast demonstrations | Conflicts with the framework constraint and narrow write rules | LangChain/LangGraph with typed, bounded tools and parameterized queries. |
| Cross-thread preference memory | More personalization | Adds identity, retention, and cross-session disclosure concerns | Required short-term graph memory only. |
| Automatic pending expiry or waitlists | Improves capacity utilization | No expiry policy, queue order, or notification workflow was agreed | Holds remain until decision/cancellation; surface age in admin records only if already available. |
| Sensor occupancy, charging reservations, maps, navigation | Makes parking look realistic | Fixtures represent scheduled reservations, not physical presence or charging infrastructure | Computed booking-interval status plus an EV-capability attribute. |
| Rich dashboard, mobile app, omnichannel notifications | More polished product | Adds surfaces and external services without validating the core booking flow | Simple chat, grid, and bookings table. |
| Unlimited-date inventory or automatic daily inventory creation | Makes every request answerable | Invents operational availability beyond fixture coverage | Explicit coverage limits and unsupported-date responses. |
| Full database/graph dumps for customer transparency | Appears useful for debugging | Exposes PII and internal state | Safe customer projection; internal evidence inspected in tests/developer tooling. |

## Behavioral Contracts and Acceptance Examples

### Availability, Grid, and Time

1. **Daily identity:** Match both spot ID and slot date. The same physical spot on different dates is distinct daily inventory. Missing inventory outside November 1–30 is unsupported coverage, not proof that everything is occupied or available.
2. **Interval truth:** The grid and chat must query the same selected interval. A November 9 snapshot value must not override a later reservation overlap check. A committed pending request and a confirmed booking both block overlaps; legacy fixture status mapping needs an explicit rule before implementation.
3. **Attributes versus state:** `electric`/EV is a spot attribute. `Available`, `Occupied`, and `Pending` describe the selected interval's booking state. An EV spot can be available, occupied, or pending. Do not make EV a fourth mutually exclusive availability status. A confirmed future booking is not evidence that a vehicle is physically present.
4. **Bounded answers:** November 11–30 inventory exists even though seeded reservation examples stop November 10; migration must permit valid new bookings against those inventory dates. Beyond November inventory or policy validity, describe the missing coverage; do not extrapolate policies or fabricate slots.
5. **Explicit timezone:** Display/parse Europe/Warsaw and preserve fixture timestamp meaning. Ask for ambiguous dates or times. A working-hours violation and an unsupported date should produce different messages.
6. **Recommended interval rule, awaiting confirmation:** Use half-open intervals, so a 10:00–11:00 booking and an 11:00–12:00 booking can coexist. Test touching endpoints, containment, partial overlap, different spots, and different dates. This is a product recommendation, not an existing approved semantic.

### Booking Lifecycle and Writes

| Trigger | Expected Persisted Result | Customer/Admin Outcome |
|---------|---------------------------|------------------------|
| A request lacks a surname | No reservation row | Ask for surname; retain other collected fields. |
| Customer corrects plate or interval | Update draft; revalidate dependent checks | Reflect corrected details; no stale availability guarantee. |
| Two sessions submit overlapping requests | At most one blocking reservation commits | Winner receives pending reference; loser receives conflict/retry guidance without the other customer's details. |
| Booking transaction rolls back | No new hold | Report request failure; never claim pending or confirmed success. |
| Booking commits but response is lost | Existing operation is recovered using durable identity | Reconcile persisted status; do not blindly create another request or assert failure. |
| Request commits as `PENDING` | Exactly one blocking hold | State awaiting administrator approval and refresh the grid. |
| Administrator approves pending request | `CONFIRMED`; interval remains blocked | Show confirmed status after the change commits. |
| Administrator rejects pending request | `CANCELLED`; hold released | Show rejection/cancellation without promising another slot. |
| Authorized customer cancels | Controlled transition to `CANCELLED` | Release hold after commit and refresh selected interval. |
| Repeated decision/cancellation | No duplicate write side effects | Return the agreed idempotent result or transition conflict; semantics must be specified. |

SQLite serializes writers but an earlier read is not a reservation guarantee. Keep overlap validation and insertion within a correctly bounded transaction; handle busy/commit failures explicitly. This recommendation follows [SQLite isolation](https://www.sqlite.org/isolation.html) and [transaction control](https://www.sqlite.org/lang_transaction.html). **External confidence: LOW per seam.**

Graph retries can repeat external writes. Derive a booking operation identity from already durable state and enforce deduplication in SQL; a graph checkpoint alone does not establish exactly-once effects. Recover an ambiguous acknowledgement by reading the operation's persisted result. See [LangGraph fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance). **External confidence: LOW per seam.**

### Retrieval, Memory, and Safe Output

| Scenario | Required Observable Behavior |
|----------|------------------------------|
| Supported facility-policy question | Answer from relevant current-scope pages; retain source/page identity in query evidence. |
| SQL price differs from retrieved policy wording | Use SQL for the numeric price; do not reconcile by inventing a third value. |
| Successful SQL lookup finds no free matching slots | Say no matching availability for that interval/type, not no information. |
| Successful retrieval has no relevant evidence | Structured judge chooses no-available-information branch; no invented policy. |
| Chroma/SQL/LLM request fails | Report the relevant temporary inability; do not silently turn failure into empty evidence. Define partial-answer behavior explicitly. |
| Query 1 completes, then query 2 starts | Query 1 evidence remains in thread history; query 2 has a distinct index. |
| SQL and vector nodes finish in either order | Same query contains both results; one update cannot erase the other. |
| A retrieval node retries | Stable evidence IDs prevent duplicate entries. |
| A prior answer showed availability | A new availability question and every reservation write refresh SQL; retained evidence is historical. |
| Session B supplies session A's thread/reservation ID | No A draft, messages, evidence, or reservation details are returned; no unauthorized cancellation. |
| User or retrieved text requests arbitrary SQL/PII | Bounded tools refuse it; output guardrail blocks unauthorized disclosure; permitted chat remains usable. |
| Customer calls slot/chat endpoints | Only slot facts and permitted own-request state are returned; raw graph/evidence/admin records stay internal. |
| Administrator inspects the bookings view | Required booking details appear only on the separate admin surface within the trusted local boundary. |

FastAPI's declared response models filter output fields, supporting distinct customer and administrator projections. Filtering is one boundary; SQL access scope and outgoing text checks remain necessary. See [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/). **External confidence: LOW per seam.**

## Feature Dependencies

```text
Inventory/date/status semantics + fixture-preserving migration
  -> shared SQL validation and transactional write service
  -> interval availability/pricing + pending holds + cancellation
  -> administrator decisions
  -> consistent chat outcomes and slot grid refresh

Explicit graph state/input/output schemas + deployed thread persistence
  -> multi-turn collection + structured intent routing
  -> parallel vector/SQL retrieval + query-indexed evidence reducer
  -> evidence judge + no-information branch + output guardrail

Server-bound browser session/thread association + customer/admin projections
  -> isolated chat, own-request cancellation, and safe slot endpoint

Graph image/deployment + Chroma/PostgreSQL/Redis readiness
  -> SDK-backed FastAPI chat integration
  -> frontend end-to-end workflow verification
```

Booking rules should precede conversational writes: the graph and admin API must invoke the same rules. Retrieval history and per-query errors should be designed before parallel nodes. Session scope should precede exposing thread state. Frontend approval flows depend on committed SQL status, not on remembered graph narration. Existing Chroma model compatibility must be verified before claiming retrieval accuracy.

## MVP Definition and Priorities

All accepted table stakes and differentiators above are **P1** for this project's v1. Do not defer approval, pending holds, isolation, the no-information branch, evidence retention, or the simple frontend merely because a generic marketplace MVP could omit them.

Deliver in coherent slices:

1. Define date/time/status/session semantics, preserve fixtures through migration, and prove the SQL booking lifecycle under concurrency.
2. Add typed graph state, persistent short-term memory, retrieval routing/reducer/judge, guarded responses, and idempotent booking tools.
3. Package the deployed graph and connect the SDK-backed API, including separate administrative routes and safe customer schemas.
4. Complete customer chat, selected-interval grid, administrator decisions, and refresh behavior; verify multi-turn, failure, privacy, and concurrency scenarios across containers.

Do not add a v1.x or v2 feature commitment during research. Potential changes such as expiration, accounts, payments, new inventory dates, or physical occupancy need explicit future scope decisions.

## Product Semantics to Settle Before Implementation

These are required scope choices, not permission gates for this research. The roadmap should assign each to the phase that first needs it.

| Unresolved Choice | Why It Matters | Recommendation / Boundary |
|-------------------|----------------|---------------------------|
| Grid default interval/date and zone selection | An unqualified green spot is misleading | Make the displayed interval explicit; ask/require selection when absent. Choose any default deliberately. |
| Meaning of `Occupied` over an interval | A future confirmed booking is not physical occupancy | Define it as blocked by a confirmed/legacy blocking reservation for the selected interval; use a legend. Confirm whether partly overlapping intervals use one priority status or show additional detail. |
| Interval endpoint convention | Touching bookings otherwise conflict inconsistently | Recommend half-open intervals; approve and test the rule. |
| Legacy lowercase `active`, `completed`, `confirmed`, `cancelled` mapping | Historical fixtures and new holds must agree | Specify the canonical public/internal enum and blocking set, including historical queries. Do not silently cancel or rewrite legacy history. |
| Past-date requests and demo clock | Current date is November 10 while much fixture data is historical | Decide whether bookings must be future relative to real time or an explicit demo clock; distinguish historical lookup from new booking. |
| Same-day versus multi-day periods | Existing inventory/FK/schema is daily and reservations are same-day | Recommend same-day v1 requests with a clear validation message; multi-day support requires explicit scope and atomic decomposition across dates. |
| Plate formats and normalization | Fixture-style plates do not define every legal vehicle format | Choose supported formats and uppercase/space handling; show useful validation feedback rather than claiming universal plate validation. |
| Type matching and zone-only requests | `electric`, accessible, van, and standard are distinct fixture types | Define exact matching versus permitted alternatives, and whether a zone request auto-selects a slot or asks the customer. |
| Total-price calculation and rounding | SQL supplies PLN/hour, not an approved billing algorithm | Show hourly rate; define duration rounding before adding a total estimate. Payments remain excluded. |
| Session lifetime, new-chat/reset, and thread association | No login does not specify browser-session ownership | Bind threads server-side to an unguessable session association; decide refresh/restart and multi-tab behavior without adding account authentication. |
| Cancellation authorization and legacy fixture bookings | Seeded reservations have no new browser owner | Define whether customer cancellation is limited to session-created requests; ID plus plate alone must not become an unintended cross-session lookup. |
| Approval/cancellation conflicts and repeats | Concurrent admin/customer updates can race | Specify permitted source states, idempotent repeats, and conflict responses; no generic arbitrary status patch. |
| Admin decision reflected into graph memory | SQL and chat can otherwise disagree | Decide refresh-on-next-turn versus explicit graph update/resume. A graph interrupt is not automatically required merely because SQL status is pending. |
| Cross-tab administrator refresh timing | Refresh in one tab does not update another automatically | Define acceptable latency and a simple refresh/poll mechanism; do not require WebSockets without need. |
| Partial retrieval failure | Successful SQL with unavailable policy evidence may support only part of an answer | Define what can be answered with an explicit limitation; never use stale availability or call a failed retrieval no information. |
| Pending lifetime | Holds can remain indefinitely under the agreed manual lifecycle | Preserve until administrator decision or authorized cancellation; expiration is a future policy choice, not a hidden timer. |

## Sources and Confidence

| Source | Supports | Confidence / Limit |
|--------|----------|--------------------|
| [PROJECT.md](../PROJECT.md) | Accepted scope, workflows, constraints, open questions | Direct project authority; not an empirical market-confidence claim. |
| [Codebase architecture](../codebase/ARCHITECTURE.md), [fixture README](../../ingested_mock_data/README.md) | Existing app gap, daily inventory, snapshot/date coverage, fixture restrictions | Local baseline; distinguish documented fixture behavior from implemented runtime features. |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Thread memory versus cross-thread stores; Agent Server persistence | LOW, code seam result for verified webfetch; official living docs accessed 2026-11-10. |
| [LangGraph state](https://docs.langchain.com/oss/python/langgraph/graph-api-state) | Reducer merge versus field replacement | LOW, same seam; verify pinned API during implementation. |
| [LangGraph fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance) | Retried side effects, durable operation identity, uncertain acknowledgement | LOW, same seam; basis for validation recommendations, not a verified application guarantee. |
| [SQLite isolation](https://www.sqlite.org/isolation.html), [transactions](https://www.sqlite.org/lang_transaction.html) | Committed-read visibility, one writer, explicit transactions and busy conditions | LOW, same seam; cross-checked primary pages. |
| [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/) | Validated, filtered output schemas | LOW, same seam; does not establish ownership or protect prose on its own. |

No external source establishes this project's product semantics. Open decisions above must be settled in planning, and implementation claims must be tested against the deployed versions and real fixture copy.

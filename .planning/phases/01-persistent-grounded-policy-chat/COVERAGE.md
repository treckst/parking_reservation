# Phase 01 Coverage and Source Audit

**Status:** Planned, not executed. All phase scope is assigned; execution gates are deliberately unproven.

## Execution Waves

| Wave | Plans | Needs → creates |
|---|---|---|
| 1 | 01-01 | Existing assets → locked runtime, conformed exact saver |
| 2 | 01-02 | Passed prerequisites → built graph/SDK/separate-file proof and browser tracer |
| 3 | 01-03, 01-06 | Proven tracer → retained evidence/context; durable owned recovery |
| 4 | 01-04, 01-07 | Prior contracts → full policy answers; browser lifecycle/interaction |
| 5 | 01-05 | Answer graph → adversarial final-only privacy evidence |
| 6 | 01-08 | Completed paths → real-corpus/live/deployed/browser acceptance and setup |

Same-wave plans have no modified-file overlap. Each plan has two tasks; every task touches at most five intended files. First work is the explicit prerequisite probe; the full browser tracer is completed and verified in 01-02 before expansion.

Scope revision: 01-02 has nine distinct files by consolidating initial HTTP/DTO/ownership and deployed checks in test_deployed_chat.py; the comprehensive independent API matrix is created in 01-06-02. 01-08 has eight distinct files: final integrated assertions extend test_deployed_chat.py only, while the existing 01-06 recovery and 01-07 browser suites remain mandatory unchanged verification inputs. Every original scenario and gate is retained. Affected scope_budget blocks give concrete task/module boundaries; counts, dependencies and six execution waves are unchanged.

## Multi-Source Coverage Audit

COVERED means executable work is assigned, not already verified.

| Source | ID | Feature/constraint | Plan | Status |
|---|---|---|---|---|
| GOAL | Phase 1 | Ask policy questions to plan parking from supported answers; deployed SDK, persistence, privacy, readiness | 01–08 | COVERED |
| REQ | GRAPH-01 | Exact model; LangChain/LangGraph only | 01, 02, 04, 08 | COVERED |
| REQ | GRAPH-02 | Typed graph/model/API/draft boundaries | 02, 03, 04, 05 | COVERED |
| REQ | GRAPH-03 | Owned persistent conversations and draft across restart | 01, 02, 03, 06, 07, 08 | COVERED |
| REQ | GRAPH-04 | Distinct query identity and retained evidence | 03, 04, 06, 08 | COVERED |
| REQ | GRAPH-06 | Same-thread rejection and durable identity | 06, 07, 08 | COVERED |
| REQ | RAG-02 | Dedicated policy vector path; no SQL branch | 02, 03, 04, 08 | COVERED |
| REQ | RAG-05 | Structured assessment, retry and abstention | 04, 08 | COVERED |
| REQ | RAG-07 | Compatible preserved corpus; scoped source/pages | 01, 02, 04, 08 | COVERED |
| REQ | PRIV-01 | Input/document injection and scoped tools | 02, 05, 06, 08 | COVERED |
| REQ | PRIV-05 | Final guard before public output | 02, 05, 08 | COVERED |
| REQ | API-01 | Deployed SDK chat and safe projection | 02, 06, 07, 08 | COVERED |
| REQ | API-05 | Pydantic, statuses, origins/CORS | 02, 05, 06, 07, 08 | COVERED |
| REQ | DEL-02 | Build/start image before SDK API acceptance | 01, 02, 08 | COVERED |
| REQ | DEL-04 | Healthy dependencies and container DNS | 02, 08 | COVERED |
| CONTEXT | D-01 | Message language | 04 | COVERED |
| CONTEXT | D-02 | Concise direct answer | 04 | COVERED |
| CONTEXT | D-03 | Inline public source/page citations | 02, 04, 05 | COVERED |
| CONTEXT | D-04 | Friendly practical tone | 04 | COVERED |
| CONTEXT | D-05 | Refresh retains thread | 07 | COVERED |
| CONTEXT | D-06 | Browser close/reopen starts fresh; strict restore matrix gate | 07, 08 | COVERED |
| CONTEXT | D-07 | New/duplicate tabs have separate threads | 07 | COVERED |
| CONTEXT | D-08 | Immediate New chat preserves old storage | 07 | COVERED |
| CONTEXT | D-09 | Separate exact SqliteSaver DB | 01, 02 | COVERED |
| CONTEXT | D-10 | Outside-graph local connection/closure | 01, 02 | COVERED |
| CONTEXT | D-11 | Postgres/Redis do not replace SQLite checkpoints | 01, 02 | COVERED |
| CONTEXT | D-12 | Exact async/hook conformance gate; no substitution | 01, 02 | COVERED |
| CONTEXT | D-13 | Compare all four if unspecified | 03, 04 | COVERED |
| CONTEXT | D-14 | Supported partial reply and unavailable gaps | 04 | COVERED |
| CONTEXT | D-15 | One semantic rewrite/retrieval/judge | 04 | COVERED |
| CONTEXT | D-16 | Same query/message identity and attempt history | 03, 04 | COVERED |
| CONTEXT | D-17 | Second failure asks new question | 04 | COVERED |
| CONTEXT | D-18 | Silent retry; explicit dependency failures | 04, 05 | COVERED |
| CONTEXT | D-19 | Final checked output only | 02, 05, 07 | COVERED |
| CONTEXT | D-20 | Editable pending draft; disabled Send | 07 | COVERED |
| CONTEXT | D-21 | Safe error/Retry preserves original turn | 06, 07 | COVERED |
| CONTEXT | D-22 | Recover accepted work without resubmission | 06, 07 | COVERED |
| RESEARCH | R-01 | Prerequisite import/model/structured-output/provenance checks | 01 | COVERED |
| RESEARCH | R-02 | Exact saver five async operations and official conformance | 01 | COVERED |
| RESEARCH | R-03 | Outside-graph lifecycle, serialization, cancellation/drain/history/delete | 01 | COVERED |
| RESEARCH | R-04 | Pinned image hook, separate file, SDK/restart evidence | 02 | COVERED |
| RESEARCH | R-05 | Responsibility map: graph RAG, API ownership, browser interaction | 02–07 | COVERED |
| RESEARCH | R-06 | Typed state, immutable evidence, deterministic IDs/current evidence | 03 | COVERED |
| RESEARCH | R-07 | Bounded four-facility/shared-source retrieval; citation mapping | 04, 08 | COVERED |
| RESEARCH | R-08 | Structured per-claim judge; partial/one-rewrite/unsupported routes | 04 | COVERED |
| RESEARCH | R-09 | Input/document injection, fail-closed final guard and no raw streams | 05 | COVERED |
| RESEARCH | R-10 | Durable reserve/create/reconcile/result ledger, reject concurrency | 06 | COVERED |
| RESEARCH | R-11 | Owned helper routes, safe projection/status/origin bounds | 02, 06 | COVERED |
| RESEARCH | R-12 | Browser copy/restore limitation, draft and recovery interaction | 07 | COVERED |
| RESEARCH | R-13 | Preserving real Chroma cases, configured live tests, reproducible setup | 08 | COVERED |
| RESEARCH | R-14 | Package identity and tested lock; no telemetry-only approval flow | 01 | COVERED |

Requirement coverage: **14/14**. Decision coverage: **D-01–D-22, 22/22**, explicitly cited in plan truths and implementing actions. Later SQL/grid/booking/admin requirements and deferred ideas are excluded by approved ownership, not silently dropped.

## API Capability Coverage

The capability surface is grouped at the relevant service boundary, starting with full coverage and making scoped exclusions explicit. These choices implement the already approved local policy-chat scope.

| capability | decision | reason |
|---|---|---|
| Agent Server SDK threads.create / owned thread binding | INTEGRATE | Required new chat/tab capability, 01-02/06 |
| Agent Server SDK runs.create / reject multitask / request metadata | INTEGRATE | Durable owned submission, 01-02/06 |
| Agent Server SDK runs.list pagination / metadata reconciliation | INTEGRATE | Required lost-create-ack recovery gate, 01-06 |
| Agent Server SDK runs.get / join / final completion | INTEGRATE | Accepted request recovery without resubmit, 01-06 |
| Agent Server state/checkpoint read for operator acceptance | INTEGRATE | Separate-file/restart proof; never public passthrough, 01-02/03/08 |
| Agent Server customer raw state/history/event/token stream proxy | OPT-OUT | D-19 permits only final checked response and safe transcript |
| Agent Server run cancel/rollback, thread delete/copy/pruning/search UI | OPT-OUT | No history browser, cancellation or automatic thread deletion requested |
| Agent Server cron, webhooks, deployments/admin management APIs | OPT-OUT | Local Compose policy-chat scope has no scheduling or platform management |
| Custom checkpointer aget_tuple / aput / aput_writes / alist / adelete_thread | INTEGRATE | All five base protocol operations including conformance cleanup, 01-01 |
| Custom checkpointer optional rollback/pruning/copy/extensions | OPT-OUT | Not required by approved policy chat; never advertise unsupported inheritance |
| Chroma heartbeat / collection metadata / bounded query / get IDs | INTEGRATE | Readiness, provenance, read-only source/page retrieval and preservation, 01-01/02/08 |
| Chroma collection add/upsert/delete/reset/rebuild/admin/tenant management | OPT-OUT | Original corpus must remain intact; no re-ingestion or platform feature |
| LangChain ChatOpenAI Responses model call / strict structured outputs | INTEGRATE | Exact model, intent/judge/rewrite/guards and schema errors, 01-01/04/05 |
| OpenAI embeddings query compatible with existing collection | INTEGRATE | Query-only embedding provenance and retrieval, 01-01/02/08 |
| OpenAI token streaming to customer | OPT-OUT | D-19 final checked replies only |
| OpenAI image/audio/video/files/batch/fine-tuning/hosted tools/realtime | OPT-OUT | Approved text policy chat and existing Chroma require none of these capability groups |
| PostgreSQL / Redis readiness and server connection | INTEGRATE | Required Agent Server infrastructure, 01-02 |
| PostgreSQL as application checkpoint replacement; booking SQL queries | OPT-OUT | D-09–D-12 lock SQLite checkpoints; availability/booking belong to later phases |
| Browser same-origin chat / owned restore / request-status polling | INTEGRATE | Refresh, tab continuity, recovery and final reply, 01-02/06/07 |
| Customer accounts/application API keys/public hosting/admin/slots routes | OPT-OUT | Explicit trusted-local access model; later slices own slots/admin |

## Spec-less Edge Probe Disposition

The source JSON is preserved unchanged. Of 20 proposals, 11 classified cases have explicit acceptance truths and 9 unclassified cases remain flagged unresolved assumptions in the owning plan frontmatter; no proposal is silently dismissed. No backstop was needed because the classified cases have defensible concrete checks.

| Requirement | Category | Disposition | Acceptance/flag location |
|---|---|---|---|
| GRAPH-01 | unclassified | FLAGGED unresolved | 01: exact-model constraint tested; probe supplies no extra semantics |
| GRAPH-02 | unclassified | FLAGGED unresolved | 03: typed boundaries tested; no invented edge resolution |
| GRAPH-03 | unclassified | FLAGGED unresolved | 01/07: restart/browser gates remain explicit |
| GRAPH-04 | adjacency | resolved / explicit | 03 truth: equal evidence IDs dedupe; conflicting immutable identity rejects |
| GRAPH-04 | empty | resolved / explicit | 03 truth: empty identity/singleton works; null rejects |
| GRAPH-04 | ordering | resolved / explicit | 03 truth: ties sort source/page/ID independent of arrival |
| GRAPH-06 | unclassified | FLAGGED unresolved | 06: concurrency policy tested without claiming classifier resolution |
| RAG-02 | unclassified | FLAGGED unresolved | 04: policy-only graph tests; no new semantics |
| RAG-05 | unclassified | FLAGGED unresolved | 04: structured/retry routes tested; no fabricated edge |
| RAG-07 | adjacency | resolved / explicit | 08 truth: stable duplicate document IDs coalesce |
| RAG-07 | empty | resolved / explicit | 08 truth: no-match insufficient; outage distinct |
| RAG-07 | ordering | resolved / explicit | 08 truth: equal score stable source/page/ID |
| PRIV-01 | concurrency | resolved / explicit | 05/06 truths: independent owners and denied SDK actions remain scoped during concurrent runs |
| PRIV-05 | unclassified | FLAGGED unresolved | 05: final guard tests; probe remains unclassified |
| API-01 | empty | resolved / explicit | 06 truth: whitespace/null messages 422 |
| API-01 | encoding | resolved / explicit | 06 truth: 4000 Unicode code points; original payload equality retained |
| API-01 | concurrency | resolved / explicit | 06 truth: same-thread 409, identical replay recovers original |
| API-05 | concurrency | resolved / explicit | 06 truth: owned typed response/status consistency under retry/race |
| DEL-02 | unclassified | FLAGGED unresolved | 01/02: real image gate; no ungrounded classifier resolution |
| DEL-04 | unclassified | FLAGGED unresolved | 01/02: real health/DNS gate remains explicit |

## Prohibition Recall

Recall/precision considered each requirement's unwanted variants: model substitution, corpus replacement, invisible evidence loss, wrong session, automatic deletion, raw internal output, fabricated policy, unintended SQL/tool use, unbounded retry and booking pressure. Routine correctness items are assigned to edge/tests; injection/IDOR/privacy canon is referred to ASVS1 threat models and $gsd-secure-phase, not duplicated as bespoke prohibitions.

One bespoke transparency candidate survives: informational policy answers must not become unsolicited pressure to reserve. It is projected through projectProhibitions into 01-04 must_haves.prohibitions, descriptor-less and unresolved; downstream disposition is flagged-unverified, never an invented green check. This is a flagged review assumption, not a new product workflow. Counts: 1 surfaced = 1 authored; no automatic dismissal.

## Assumption Delta and Schema Gate

The detector fired only on "another session". **No-change:** primary identity remains server-session-owned thread/request; no second tenant/platform feature is introduced. 01-06 records the decision. No Prisma/Drizzle/Payload/Supabase/TypeORM schema paths are in scope; no ORM push is applicable.

## Genuine Execution Gates

1. Exact synchronous saver bridge must pass five async operations, lifecycle/concurrency and the pinned custom Agent Server hook with separate-file SDK/restart evidence.
2. Exact-model account/structured-output, embedding provenance/imports and server entitlement/readiness must be verified without substitution or original-data mutation.
3. Pinned run list/metadata reconciliation must prove lost-ack recovery; uncertain acceptance cannot trigger blind recreation.
4. Actual target-browser close/reopen/restoration must satisfy D-06 alongside D-05 refresh. If not technically distinguishable, report concrete evidence and seek a scoped user decision before accepting the phase.
5. All required Chroma/deployed/live/browser checks remain unverified when skipped/unavailable. Planning is complete; no execution check is claimed passed.

## Planning Evidence

Discovery uses the existing current research; no repeat web research. No prior summaries/verification commands existed. Graph context is disabled. Estimate calibration: factor 1, sample count 0, derived confidence low. No application source/state/roadmap edits, branch changes or commits are part of this planning assignment.


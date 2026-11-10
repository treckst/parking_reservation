# Walking Skeleton — Parking Reservation Assistant

**Phase:** 1
**Generated:** 2026-11-10
**Status:** Planned, not executed

## Capability to Prove End-to-End

A customer asks one supported policy question in the local browser and receives a guarded cited answer through FastAPI, the SDK, a built Agent Server image, real Chroma and a real separate SQLite checkpoint write/read; restarting the graph retains the conversation.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | Python 3.12, LangChain/LangGraph, FastAPI, plain HTML/CSS/ES modules | Approved stack; no extra agent/frontend framework |
| Model | Exact gpt-6-luna via LangChain with structured schemas | Locked requirement; account access must pass 01-01 |
| Policy data | Existing parking_documents Chroma collection, compatible embeddings | Preserve source/page identities and existing assets |
| Checkpoints | Exact synchronous SqliteSaver; separate checkpoint SQLite file | D-09–D-12; adapter conformance and actual server hook remain execution gates |
| Connection lifecycle | generate_checkpointer outside graph, local connection/closure, drain then close | D-10; never state/runtime-context connections |
| Server infrastructure | PostgreSQL and Redis | Agent Server resources; do not replace requested SQLite checkpoints |
| Ownership/recovery | Server-issued session cookie plus durable owner/thread/request registry in another SQLite file | Server scope precedes every SDK action; tab identity is UX only |
| Access model | Trusted local demo, no login/application keys | Approved boundary; provider/server secrets stay server-side |
| Deployment | Pinned built Agent Server image, Compose healthy dependencies, then SDK API/static frontend | Graph starts before API hookup; no in-process fallback |
| Layout | src/parking/{settings,checkpoint,retrieval}.py; graph/, api/, web/; tests/{unit,integration,live,web} | Small readable responsibilities without operational seed imports |

## Stack Touched in the Skeleton

These are pending acceptance checks, not claims of implementation.

- [ ] Scaffold: locked authorized dependencies, runtime/import/model/embedding gates and meaningful pytest fixtures (01-01).
- [ ] Route: owned POST /api/chat and safe create/restore/status helpers (01-02).
- [ ] Database: real checkpoint write/read in separate SQLite, real Chroma read and restart continuity (01-02).
- [ ] UI: one actual browser submit receiving only final checked text through API/SDK (01-02).
- [ ] Deployment: built graph image with Chroma/PostgreSQL/Redis readiness, then API (01-02).

## Execution Sequence

01-01 is a prerequisite technical probe: imports/model/provenance and five-method saver conformance. It does not count as the browser tracer. 01-02 proves the deployed graph first and completes the browser walking skeleton in its second task. No policy expansion starts until that full tracer is verified. Plans 01-03/06 then expand independent evidence and recovery concerns.

The checkpoint DB read/write meets the skeleton database criterion; Phase 1 does not write booking data.

The shared test_deployed_chat.py proves both the graph image and its initial owned HTTP/browser entry in 01-02 (nine distinct files). The independent API matrix is created in 01-06; final 01-08 assertions extend the shared deployed tracer and rerun existing recovery/browser suites unchanged. The skeleton remains intact and final acceptance touches eight distinct files.

## Acceptance Gates

- Exact saver adapter conformance, pinned custom hook, SDK round trip, separate-file evidence and restart continuation.
- Exact model/account/structured output and embedding provenance; no silent fallback or automatic re-ingestion.
- Lost-create-acknowledgement reconciliation and target-browser refresh/close/reopen/restored-tab behavior.
- D-06 remains unverified if the browser cannot distinguish restored sessions from refresh; report the conflict and obtain a scoped decision before acceptance.
- Required external skips or unavailable prerequisites remain unverified.

## Out of Scope (Approved Later Slices)

Live SQL availability and slot grid; booking migration/overlap allocation; customer booking writes; administrator decisions/cancellation; public deployment/accounts/payments/history browser/automatic deletion.

## Subsequent Slice Plan

- Phase 2: SQL availability, pricing and the slot grid, retaining this session/evidence boundary.
- Phase 3: Conversational pending reservation writes with transactional overlap safety.
- Phase 4: Administrator decisions, cancellation and consistent refresh.


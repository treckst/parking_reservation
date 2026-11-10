---
status: complete
commit: a124b86
date: 2026-11-10
---

Implemented the API-only administrator approval flow using compiled policy,
reservation and admin subgraphs directly mounted in the main graph.

- Structured extraction and intent summarization precede an idempotent pending
  SQLite write. The admin interrupt happens before the mock continuation.
- The admin graph waits for API-supplied review text and invokes its own strict
  structured-output LLM. A parent conditional edge routes approve to mock_node
  and reject to hold release/customer completion.
- Subgraph output schemas restrict updates to owned keys. Message IDs and
  immutable query/evidence reducers preserve conversation state across resume.
- Additive booking_requests rows preserve legacy fixtures and hold slots while
  pending. BEGIN IMMEDIATE protects checks/inserts against competing writers;
  both legacy blocking rows and new holds participate in overlap checks.
- Admin listing/review endpoints verify the paused checkpoint, claim review
  dispatch once, and reconcile uncertain acceptance without another resume.
  Customer polling remains pending at the interrupt and follows continuation.
- BOOKING_DB_PATH and shared Compose mounts let API and graph use the same
  booking file. README and docs/admin-approval.md describe setup/API behavior.

Validation: 56 offline Python tests passed across unit, admin flow, API contract,
recovery, checkpointer conformance and browser contract suites. Three JS browser
controller tests passed. Compose config --quiet exited successfully. One existing
LangChain community deprecation warning remains. The Windows asyncio network
guard fixture now initializes its runner before blocking outbound sockets.

No live model calls, image rebuilds or deployment were performed. Rebuild graph
then API to activate this source change. Missing fixture files fail closed.
Unresolved resume acceptance stays creating for operator investigation; no
absence-of-match retry is inferred. Mock continuation performs no external work.

Execution was inline and sequential per skill spawn restriction and project
configuration. Pre-existing .env.example, PROJECT.md and Compose tracing edits
were excluded from the implementation commit; unrelated untracked files remain.

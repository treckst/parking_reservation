---
status: complete
commit: 4a89412
date: 2026-11-10
---

Corrected the implemented reservation flow to match the user's intended compiled-subgraph architecture.

- Customer extraction accumulates reservation details and persists a valid pending SQLite hold before summarization. The saved intent, unique reservation_id and normalized booking_draft share named channels with the admin subgraph.
- Admin retains its API review/resume boundary and separate structured LLM decision. A fixed tool-call adapter executes that decision in a real LangGraph ToolNode. The reservation ID and decision come from injected state.
- The tool rechecks hours and overlaps under BEGIN IMMEDIATE, excluding its own hold, and updates the existing row to approved/rejected. No unvalidated insert fallback is permitted. Replays preserve the durable result, including rejection on rule failure.
- Transactional schema migration preserves existing application confirmed requests as approved, along with identities, summaries, drafts and dispatch claims. Legacy fixtures remain unchanged.
- Private admin message/decision channels stay inside AdminState. Only admin_result returns through AdminOutput; the parent validates its ID and builds the reply without writing reservation status. Removed parent mock/reject write nodes.
- Updated README and operator documentation with shared-key handoff, statuses, tool ownership and migration behavior.

Validation: 88 offline Python tests passed (3 external tests deselected), including 16 focused admin integration tests; 3 JavaScript controller tests passed. Changed-file git diff --check passed. Existing LangChain community deprecation warning remains. Initial sandboxed test collection could not load a NumPy DLL; the approved outside-sandbox run completed successfully with mocked providers.

No live model calls, deployment, container rebuild or changes to the existing booking fixture were performed. Already-paused checkpoints from the previous graph shape are not migrated by this task; finish those runs before deploying the new graph. Rebuild graph then API to activate source changes. Pre-existing edits in .env.example, PROJECT.md and docker/compose.yaml were excluded from commits.

Executed inline and sequentially per the skill spawn restriction and project configuration. ROADMAP.md was not changed.

---
type: quick
status: planned
---

Persist pending reservations before summarization and finalize them inside the compiled admin subgraph.

1. Share reservation_id, booking_draft, reservation_summary and admin_result across graph boundaries; isolate admin tool messages from customer history.
2. Collect complete details and persist a transactional pending hold, then summarize the stored intent for admin review. Keep the existing administrator API authorization boundary.
3. Run the admin LLM decision through a ToolNode that updates the same SQLite row to approved/rejected, with transactional rule revalidation and replay safety. Migrate prior confirmed request rows without changing legacy fixtures.
4. Make the parent reply from durable admin_result; remove mock write nodes. Cover nested handoff/restart, missing details, rule failures, migration, replay and privacy; update operator documentation and STATE.md.

Execution: inline and sequential under the skill's spawn restriction and workflow.use_worktrees=false. No deployment or live model calls.

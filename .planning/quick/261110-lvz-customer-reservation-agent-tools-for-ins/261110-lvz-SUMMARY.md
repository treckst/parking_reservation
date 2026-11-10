---
status: complete
date: 2026-11-10
---

Implemented a real customer LLM/tool loop rather than structured extraction alone.

- Matched customer draft fields to seed_database.py: name, surname, car_number, spot_id, start_time/end_time (draft start/end). Date is derived and ID/status/creation metadata are application-owned. Existing additive booking_requests persistence remains in use; no fixture or schema regeneration.
- Bound four tools to the LLM with sequential calls: inspect current draft, merge partial updates, ask for actual missing fields, and request submission. Real ToolNode execution returns updated state snapshots to the LLM before its next action.
- Draft fields persist in shared booking_draft across turns/checkpoint restarts; omitted values survive and explicit null clears fields. Tool schemas reject arbitrary state/admin/thread mutations. Private tool history never reaches customer DTO/history.
- Pending writes require an explicit submit tool call and deterministic completeness check, then existing transactional database validation. Premature submit loops back without writing. Follow-up questions list only missing fields and do not echo personal values. Model free text cannot authorize a write or leak into the customer reply.
- Bounded collection to six model/tool steps. Preserved compiled reservation/admin handoff and admin_result finalization.
- Updated operator documentation and README.

Validation: 93 offline Python tests passed, 3 external cases deselected; 3 JavaScript tests passed. Five new collection integration cases cover current-state visibility, partial collection/restart/correction, premature submission, unauthorized state fields, free-text output handling and bounded tool loops. Existing 16 approval integration cases also pass. Changed-file whitespace check passed. Existing LangChain community deprecation warning remains.

Execution was inline/sequential per skill spawn restriction and project configuration. No live provider calls, seed execution, container rebuild or deployment. Existing paused checkpoints are not migrated to the new graph topology; finish existing runs before deployment. Pre-existing unrelated changes were excluded. ROADMAP.md unchanged.

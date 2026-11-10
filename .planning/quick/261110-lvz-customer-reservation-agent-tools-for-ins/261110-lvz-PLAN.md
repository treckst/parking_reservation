---
type: quick
status: planned
---

Give the customer reservation LLM a real tool loop to inspect/update its scoped draft, ask for missing fields, and request submission only when complete.

1. Map seed_database.py reservation columns to customer fields: spot_id, name, surname, car_number, start/end; derive slot_date, reservation_id, status and creation metadata in application code.
2. Bind inspect/update/ask/submit tools to the customer LLM and execute through a private ToolNode loop. Merge partial updates across turns; keep internal tools out of customer history and protect non-draft state.
3. Gate pending SQLite writes on complete details and explicit submission tool; preserve existing transactional validation and compiled admin handoff.
4. Test real tool execution, incremental collection/restart, missing-field prompts, correction, invalid/early submission and privacy; update docs and GSD state and commit scoped changes.

Execute inline, sequentially. No provider calls or deployment.

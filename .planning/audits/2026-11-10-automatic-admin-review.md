# Automatic admin review audit

Source: gsd-audit-fix / audit-uat (no saved UAT findings), user report and live checkpoint inspection.

The supplied thread has a committed pending request, next node `admin`, one interrupt and no error. No review has been claimed and final_reply is empty. The admin graph deliberately interrupts before its LLM. The user clarified that the admin is an automatic subgraph receiving shared state keys, reviewing the saved intent, then approving or rejecting without human input. This supersedes the previous human-review API design for this workflow.

| ID | Severity | Classification | Finding / intended fix |
|---|---|---|---|
| F-01 | high | auto-fixable | Human-only await_review blocks the required automatic admin agent and leaves committed requests without a customer result. Run structured review on the shared saved draft/summary, execute the fixed persistence ToolNode transactionally, return admin_result, and safely recover checkpoints already paused by the old graph without creating a second request or approval continuation. |

Checks: automatic approval and rejection, shared handoff keys, durable row identity, SQL revalidation, confirmed-row transaction, privacy, checkpoint replay/restart, old interrupt recovery, duplicate dispatch/lost acknowledgement, and customer final response. The original pending request must survive deployment and be recoverable without resubmitting its booking details.

## Result

F-01 fixed in `66a1547`. The shared handoff is checked against the scoped durable request, then strict structured admin review runs automatically and its fixed ToolNode executes the existing atomic finalization. Replays reuse the persisted result. The retained `await_review` node name supports old checkpoints, but it no longer interrupts. The API provides decision-free `/resume` recovery; the obsolete human `/review` endpoint is removed. Customer polling can recover matching legacy interruptions with durable dispatch claims, identity checks and lost-acknowledgement reconciliation.

Verification: 179 Python tests passed, 3 opt-in deployed tests skipped; existing retriever deprecation warning only. Coverage includes automatic approve/reject, saved handoff mismatch, invalid model output/provider failure, SQL rules, confirmed-row insertion/rollback, private subgraph state, genuine SQLite-saved old interrupt upgrade, duplicate/concurrent recovery, API restart, lost acknowledgements and cross-thread rejection. `git diff --check` passed.

Rebuilt graph source and API images and recreated Compose services; all five services are healthy. The original pending request `dda64dc5-b9ce-581d-9aee-1322b4496aad` was resumed through the recovery API. Its actual admin LLM approved it, the continuation run finished successfully, and exactly one confirmed reservation exists. Spot, interval, name, surname and plate match the saved request (checked without printing personal fields). The final checkpoint has no remaining tasks and returns `The administrator approved your reservation.` Existing chat polling reconnects to this continuation.

Fixed 1/1 auto-fixable findings. No manual-only findings remain in this scoped audit.

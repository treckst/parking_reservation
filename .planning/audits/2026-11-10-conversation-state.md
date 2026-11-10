# Conversation state audit and fixes

Source: gsd-audit-fix / audit-uat plus reported screenshot and attached runtime log.
The audit-uat query returned no existing UAT/verification findings.
Execution: inline (project parallelization disabled; no explicit subagent request).

| ID | Severity | Classification | Finding / verification |
|---|---|---|---|
| F-01 | high | auto-fixable | Classifier truncates history and lacks draft context; collector drops assistant turns and relies on optional model inspection. Verify mandatory inspection, contextual routing payload, restart preservation and thread isolation. |
| F-02 | high | auto-fixable | No separate natural-language date extraction boundary; nonblank invalid dates count as ready. Add structured extraction with Warsaw reference time, clarify ambiguous dates, validate timestamps and intervals. |
| F-03 | medium | auto-fixable | Compose sets project alongside Agent Server agent destination, causing EnvAddressError. Remove conflicting destination and test SDK resolution. |

Customer output remains scoped; evidence reducer and SQLite overlap transactions remain authoritative.
Unrelated pre-existing worktree changes must be preserved.

F-01: fixed in 5d132be; 58 state/history/booking/unit checks passed.
F-02: separate ReservationDates normalization, validated Warsaw timestamps,
interval readiness, and sole ownership of date changes. Full role-labelled
context is supplied to extraction. 71 unit/booking checks passed, including
restart/correction/isolation and the reported natural-language interval.
Provider calls in these automated tests are scripted; live validation is separate.

F-03: Compose clears project destinations and legacy aliases for the graph,
retaining Agent Server's agent address and runtime credential. Synthetic env_file
tests exercise the actual installed SDK resolver from root and docker/.
Full regression gate: 111 passed, 3 skipped (opt-in deployed checks), with one
existing langchain-community deprecation warning. No fixture/Chroma reseeding.

## Deployed verification

Rebuilt parking-graph:phase01 and the API image; Compose reports all five services
healthy. Existing volumes and checkpoint files were retained.

Live configured-model check used explicitly fictional Sample Customer / DEMO123
values in a fresh thread. A request with the reported English interval saved
2026-11-13T14:00:00+01:00 through 2026-11-13T21:00:00+01:00 and asked only for
spot ID and plate. A plate-only follow-up retained the dates and customer fields,
then asked only for spot ID. An ambiguous 11/12 correction cleared the affected
dates and requested clarification. Policy evidence survived all booking turns;
the checkpoint contained all six messages before the ambiguity turn. No booking
was created. No EnvAddressError/indexed-run/graph errors appeared during the check.

Automatic approval review rejected replaying the pasted real name through the
live model. The successful replay used fictional data only. Exact pasted wording
is covered with scripted model responses in automated tests.

Fixed: F-01 (5d132be), F-02 (1e95400), F-03 (0656b10).
No remaining manual-only findings in this scoped audit.

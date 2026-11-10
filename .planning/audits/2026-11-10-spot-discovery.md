# Spot discovery audit

Source: gsd-audit-fix / audit-uat (no existing UAT findings), user conversation,
and seed_database.py schema. Execution inline; no subagents requested.

| ID | Severity | Classification | Finding and expected fix |
|---|---|---|---|
| F-01 | high | auto-fixable | Collection has no spot discovery query. Add parameterized SQLite lookup with mandatory facility prefix, exact date when given, operating hours and overlap checks for complete intervals, and public spot/rate/cost projections only. |
| F-02 | high | auto-fixable | Date/duration disappear if exact times are unclear. Persist separate search preferences, normalize date without inventing a start, and derive end from a confirmed start plus duration. |
| F-03 | medium | auto-fixable | Customer is asked for internal spot ID without options. Supply compact database-backed choices/prices and contextual start/selection questions before personal details; explain a spot ID as a space label. |

Preserve checkpoint history and immutable per-query evidence. Pending and approved
requests block overlaps; actual writes still revalidate under BEGIN IMMEDIATE.
Date-only candidates must not be claimed available for an unspecified interval.
No fixture regeneration, PII projections, model-generated SQL or unfiltered reads.

## Automated verification

F-01: e0e5301; scoped lookup/booking-write checks passed (27 tests).
F-02: 3639346; independent date/duration and follow-up checks passed (92 tests).
F-03: database-backed choices, staged concise replies, ID explanation, validated
space selection, lookup-only submission guard and immutable SQL evidence.
Full suite: 138 passed, 3 opt-in deployed tests skipped. One existing community
retriever deprecation warning. Existing tests expecting an unexplained spot-ID
request were updated to verify the new space-choice workflow.

F-03 commit: 9d1cdf8. Three JS controller tests also passed.

## Deployed verification

Rebuilt graph and API images and updated the local Compose stack; all five
services healthy, volumes preserved. The configured-model replay passed the
user's exact help/evening/spot-ID conversation and subsequent follow-ups:

- City Centre, November 20, six hours: CTR-001/002/003, 8 PLN/hour and 48 PLN
  for six hours; exact start requested, no name/plate/unknown-ID demand.
- Spot-ID question: explained space labels while retaining date/duration/prices.
- '4pm': normalized to November 20, 16:00-22:00; checked interval availability.
- 'the first one': selected CTR-001, then asked for missing personal details.
- 'Airport instead': cleared the City Centre selection, queried AIR prefix on
  the same date and interval, and offered AIR-001/002/003 at 5 PLN/hour / 30 PLN.

Inspected saved SQL evidence: all lookups had a facility and exact date filter,
every returned label matched its prefix, and prior query evidence remained
unchanged. No customer names/plates were used and no hold was created. No graph
or tracing errors during the live check. All three findings fixed; no remaining
manual-only findings in this scoped audit.

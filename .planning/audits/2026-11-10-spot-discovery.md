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

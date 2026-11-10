---
phase: quick
plan: 261110-qec
subsystem: booking
tags: [sqlite, langgraph, reservations, state]
requires: []
provides:
  - Current draft readiness reports missing first name, surname, plate, space and visit interval fields.
  - Approval atomically writes a confirmed reservation and marks its pending request approved.
affects: [booking, admin-approval, availability]
tech-stack:
  added: []
  patterns: [transactional request promotion, preserving SQLite table migration]
key-files:
  created: []
  modified:
    - src/parking/bookings.py
    - src/parking/graph/collection.py
    - src/parking/graph/discovery.py
    - tests/integration/test_admin_flow.py
    - tests/integration/test_reservation_collection.py
    - tests/integration/test_spot_lookup.py
    - tests/integration/test_parking_discovery_flow.py
    - README.md
    - docs/admin-approval.md
key-decisions:
  - Keep requests in booking_requests while pending; approval inserts a confirmed row into reservations in the same BEGIN IMMEDIATE transaction.
  - Remove only the seed fixture's November 1-10 constraint while copying all existing reservation columns and rows.
  - Once a space is selected, ask for missing timing and identity details together where possible.
patterns-established:
  - SQLite migrations create a replacement table, copy records, swap names, and restore the booking lookup index.
requirements-completed: []
duration: 12min
completed: 2026-11-10
status: complete
---

# Quick Task 261110-qec Summary

**Booking replies surface all required fields, and administrator approval now promotes the pending request into the confirmed reservations table atomically.**

## Accomplishments

- The current saved draft is authoritative for missing-field prompts. When a space is selected, the assistant asks for remaining name, surname, vehicle plate, and visit timing instead of asking only about time.
- Admin approval revalidates the slot, inserts a `confirmed` row with the same reservation ID and customer fields, and marks `booking_requests` approved in one SQLite transaction. Insert failure rolls back the request status.
- A preserving migration removes the seed-only November 1-10 date constraint while retaining existing reservation rows. November 11-30 approvals are supported.
- Rejection still creates no confirmed reservation, and repeated approval does not create a duplicate row.

## Verification

- Focused tests: 28 passed.
- Full Python suite: 171 passed, 3 skipped; one existing `langchain-community` deprecation warning.
- `git diff --check`: passed.
- Migration and approval tests use temporary SQLite databases; the checked-in fixture database was not modified.

## Deviations from Plan

- The checkout was on protected `master` and GSD's commit guard rejected commits there. Work was committed on the dedicated `quick/261110-qec` branch.

## Task Commit

- `5a1fc17` — `fix(261110-qec): complete booking state and approval promotion`

## Issues Encountered

- The initial migration test exposed a malformed transformed `CREATE TABLE` statement; the constraint removal was corrected and the focused and full suites passed afterward.

## User Setup Required

None.

## Self-Check: PASSED

- Summary exists at the planned quick-task path.
- Commit `5a1fc17` is an ancestor of the current task branch.

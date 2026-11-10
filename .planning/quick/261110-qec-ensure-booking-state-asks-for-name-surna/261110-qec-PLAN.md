# Booking completeness and approval persistence

The customer booking flow must use its merged state to identify every missing required field, including first name, surname, vehicle plate, selected spot, start and end. Requests stay pending in `booking_requests`; approving one must atomically create its confirmed row in `reservations` and finalize the request.

## Tasks

1. **Make missing-field prompts state-authoritative.** Trace extraction, `ReservationCollector.prepare`, `inspect_reservation_draft`, and reply rendering. Ensure the collector inspects the merged saved draft and returns a prompt naming exactly the missing fields; never let stale model text or a partial current turn hide `name`, `surname`, or `car_number`. Cover a draft containing only spot/date/times and partially completed identity fields, plus checkpoint restart, with tests proving each value persists and pending submission is blocked until all required values exist.

2. **Promote approved requests transactionally.** Update `BookingStore.decide` and schema initialization/migration in `src/parking/bookings.py`: leave pending/rejected requests in `booking_requests`; within one SQLite write transaction revalidate availability, insert a `reservations` row with the same reservation ID, spot/date, timestamps, name, surname, car number, `confirmed` status and required creation timestamp, then mark the request approved. Make approval replay-safe and preserve legacy request rows and fixture reservations. The existing `reservations` fixture has a date-range check limited to November 1–10, while slot fixtures span November 2026; replace/upgrade that constraint additively without losing legacy data so approved November 11–30 requests can be recorded. Reconcile availability reads so pending requests and confirmed reservations continue to block overlaps without double-counting a promoted request.

## Verification

- Add focused tests in `tests/integration/test_reservation_collection.py` and `tests/integration/test_admin_flow.py` for exact missing identity fields, preservation across turns/restarts, no pending write while incomplete, approved-row insertion, rejection without insertion, idempotent replay, overlap race/revalidation, migration preserving existing fixture rows, and approval on a date beyond November 10.
- Run the full Python suite with `.venv/Scripts/python.exe -m pytest -q --tb=short -p no:cacheprovider`.
- Inspect the initialized schema and resulting rows in a temporary SQLite database; do not reseed or alter the checked-in fixture database as part of tests.

## Acceptance

- When a customer has supplied only a space and visit times, the assistant asks for first name, surname, and vehicle plate; if some are already saved, it asks only for the remaining fields.
- No incomplete booking can create a pending request.
- Approval creates exactly one matching confirmed `reservations` row and marks the source `booking_requests` row approved in the same transaction; failure leaves neither side partially updated.
- Rejection leaves no confirmed row; repeated approval is idempotent; legacy reservations remain intact and continue to enforce interval conflicts.

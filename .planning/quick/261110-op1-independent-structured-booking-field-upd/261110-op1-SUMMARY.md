---
status: complete
---

# Independent structured booking field updates

Code commits: 457dcbb, cacf25c, 5d73b03.

Mandatory ReservationExtraction now emits explicit field operations, replacing
the provided_fields/null ambiguity. Every customer field is normalized and
applied independently before SQL and the collector tool loop. Valid siblings
survive an invalid timestamp, unavailable space or another field's clarification.
Names/plates are saved even when timing or selection remain incomplete. Tools
use an explicit patch list and cannot accidentally clear omitted fields.

Omitted years use the existing visit year or the next named month/day occurrence
from Warsaw reference time. Standard/electric/accessible/van preference is stored
separately from space ID and is applied to SQL. The public projection now includes
date, duration and type alongside facility/space/start/end, never personal fields.

Readiness includes unresolved field errors at inspection, submit and pending-write
boundaries. Conflicting duration/time constraints are retained for clarification;
unknown supplied dates cannot broaden SQL. Replies are derived from merged state
and include the resolved interval, rather than agent-generated stale questions.

Verification: 159 Python tests passed, 3 opt-in deployed tests skipped. Coverage
includes the exact screenshot interval, start-only/end-only changes, explicit
clears, malformed siblings, schema forbidden keys/required operations, checkpoint
restart, pre-inspection extraction and refusal to write pending until unresolved
fields are corrected. The existing community-retriever deprecation warning remains.

Deployed graph and API images; all five Compose services healthy and existing
volumes/checkpoints preserved. The final routing-only source layer was built on
the fully rebuilt/validated LangGraph image; dependency configuration is unchanged.

The first live replay exposed the introductory booking-help query taking the
policy route and hitting its safety guard. The classifier now explicitly treats
named-location reservation assistance as collection; the guard stays intact.

Final configured-model replay passed the exact screenshot wording, including
"standart", omitted year and mixed 12/24-hour clocks. Public state and checkpoint
saved AIR, standard, 2026-11-24, 15:00-20:00, five hours. Reply quoted 25 PLN and
asked which space, rather than repeating the missing-date response. End-only
correction to 19:30 retained 15:00 and quoted 22.5 PLN / 4.5 hours. Start-only
correction to 14:30 retained 19:30 and quoted 25 PLN / five hours. Selecting the
first option saved AIR-001 and asked only for first name, surname and plate.
No personal data or hold was created; earlier evidence remained unchanged.

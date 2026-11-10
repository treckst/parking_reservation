# Contextual space choice audit

Source: gsd-audit-fix / audit-uat (no saved UAT findings) and exact screenshot.
Execution inline; no subagents requested.

History check: PASS. Classifier receives prior user/assistant messages; mandatory
extractor and collector receive the full role-labelled conversation. The failure
is choice interpretation: spot_type=standard survives, but spot_id stays empty.

| ID | Severity | Classification | Finding / fix |
|---|---|---|---|
| F-01 | high | auto-fixable | A type answer after an offered space choice is treated only as a preference. Add explicit structured choice intent and durable pending-question context; choose a freshly available matching space, disclose its label and advance. Ambiguous/deferred/information-only replies cannot silently choose or loop on the same question. |

Required checks: assistant turns in extractor payload, exact type-acceptance
follow-up, checkpoint restart, old checkpoint compatibility, fresh overlap checks,
selection/type distinction, defer/ambiguity, and no premature hold/PII disclosure.

## Result

F-01 fixed in 5e06b21. Explicit structured space_choice distinguishes accepting
an offered type from a preference, defer or unclear answer. Pending-question
context is checkpointed; existing older checkpoints use the controlled last
assistant prompt as a compatibility fallback. Fresh scoped SQL chooses a real
available label for clear type acceptance; the reply discloses the selection and
asks for missing personal fields. Unclear acceptance gets a focused question,
whose 'yes' confirmation also advances. Deferred/unclear choices cannot submit
even a complete draft. Information-only requests cannot auto-select.

Verification: 167 Python tests passed, 3 opt-in deployed tests skipped. Tests
cover full assistant/user history in the extractor, saved question context after
restart, an offered space becoming held before acceptance, no initial automatic
selection merely for a type preference, defer/ambiguity/lookup-only behavior and
no submission despite an over-eager tool call. Existing retriever deprecation
warning only.

Updated the graph source image on its validated dependency/runtime image and
rebuilt the API image. All five Compose services healthy; volumes preserved.
The exact live configured-model replay passed:

1. Airport / November 24; then 'starting at 4pm up to 20:00' -> AIR-001/002/003
   standard, 5 PLN/hour, 20 PLN for four hours, asking which space.
2. 'i would like the the standard place' -> selected AIR-001 (standard), retained
   2026-11-24 16:00-20:00 and 20 PLN; asked first name, surname and vehicle plate.
3. Public state/checkpoint contained the selection and cleared the waiting flag.
   Earlier query evidence remained unchanged. No name/plate was used and no hold
   was created. The prior assistant offer was present in the saved messages.

Fixed 1/1 auto-fixable findings; no manual-only findings in this scoped audit.

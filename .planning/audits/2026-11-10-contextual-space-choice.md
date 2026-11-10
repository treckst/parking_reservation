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

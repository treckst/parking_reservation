---
phase: 01-persistent-grounded-policy-chat
plan: "03"
status: implemented_unverified
key-files:
  created: [src/parking/graph/schemas.py, src/parking/graph/reducers.py, tests/unit/test_state.py]
requirements-completed: []
---

# Query identity and retained evidence

Immutable query records retain original message and retrieval question. The
copied-map evidence reducer preserves both attempts and previous questions,
deduplicates documents, sorts identities and rejects conflicts. Request identity
and deterministic message IDs support replay. Typed intent resolves contextual
facility follow-ups or expands to all four facilities. Booking draft is retained
without booking SQL access.

Shared implementation is in 9d30711; focused test artifacts are in 6ccff03.
Added reducer law/conflict tests, contextual intent tests and operator-only
deployed-file state inspection. The latter needs a disposable two-turn thread.

## Self-Check: SKIPPED

User requested --no-verify. New tests and deployed persistence assertions were
not run. The schema extraction happened directly in the final module layout
rather than maintaining duplicate temporary contracts in graph.py.

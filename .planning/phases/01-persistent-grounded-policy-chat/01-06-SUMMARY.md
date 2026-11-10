---
phase: 01-persistent-grounded-policy-chat
plan: "06"
status: implemented_unverified
key-files:
  created: [src/parking/api/submissions.py, src/parking/api/gateway.py, tests/integration/test_recovery.py]
requirements-completed: []
---

# Owned remote requests and crash recovery

Commit db5dbb0 adds unpredictable owner cookies, durable owned threads and a
transactional submission ledger in the separate application SQLite DB. Unique
active-thread index enforces contention across API processes. Exact message
fingerprints reject changed-payload replays. SDK runs use request metadata,
reject multitask strategy and durable checkpoints. Lost acknowledgements retain
uncertainty; paginated list reconciliation binds one matching accepted run.
No absence-only conclusion causes automatic recreation. Confirmed terminal
failure permits a conditional retry of the same question identity.

Public create/chat/conversation/request-status routes enforce ownership before
SDK operations and return safe projections. Mocked tests cover contention,
replay, lost acknowledgement, no-match uncertainty, validation, ownership and
raw-state filtering. Full cross-process crash/race and deployed SDK capability
matrices are not yet demonstrated. Conservative uncertain requests can require
operator investigation instead of automatic completion.

## Self-Check: SKIPPED

No new tests or deployed reconciliation probes run under --no-verify.

---
phase: 01-persistent-grounded-policy-chat
plan: "05"
status: implemented_unverified
key-files:
  created: [src/parking/graph/guards.py, tests/unit/test_guards.py]
requirements-completed: []
---

# Input and final reply guards

Structured input decisions precede query allocation/retrieval. The graph has no
SQL, shell, booking or arbitrary URL tools. Document metadata is allowlisted.
Every generated claim must cite judge-supported current evidence; paths, common
secret patterns and email addresses are structurally rejected. A final structured
guard is the sole assistant publisher. API DTOs and conversation restore exclude
internal candidates, state and events; exceptions use fixed customer-safe codes.

Implementation: 9d30711 and db5dbb0. Focused guard tests: 188bb28. Graph tests
also cover blocked input and failed final guard. This is not a complete executed
adversarial privacy/security audit; model-based semantic decisions remain a limit.

## Self-Check: SKIPPED

No privacy/security verification or test execution under the user's override.
No high-severity threat is marked resolved merely from authored code.

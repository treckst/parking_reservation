---
phase: 01-persistent-grounded-policy-chat
plan: "04"
status: implemented_unverified
key-files:
  created: [src/parking/graph/nodes.py, tests/unit/test_policy_flow.py]
requirements-completed: []
---

# Bounded grounded policy workflow

Structured intent and evidence assessment drive supported/partial composition,
one semantic rewrite, or friendly unsupported answers. Original query identity
survives rewriting. Current-attempt evidence is selected explicitly; facilities
are retrieved separately with shared policies. Dependency/model/schema failures
propagate as service failures rather than semantic insufficiency. Public citation
text is constructed from approved titles and one-based page numbers.

Implementation: 9d30711. Mocked compiled-graph tests: ff1c749. Corpus cases are
grounded in the supplied first pages, read with pypdf during implementation.
The stored-vector Chroma test proves read-only identity, not semantic accuracy.
The reviewed rewrite case is specified, but an end-to-end real second-retrieval
controlled-causality execution has not been demonstrated.

## Self-Check: SKIPPED

No new tests or live/provider calls run under --no-verify. Full bilingual,
comparison, partial-support and rewrite semantic acceptance remains unverified.

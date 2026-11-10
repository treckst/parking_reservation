---
phase: 01-persistent-grounded-policy-chat
plan: "08"
status: implemented_unverified
key-files:
  created: [README.md, tests/cases/policy_cases.json, tests/integration/test_chroma_retrieval.py]
requirements-completed: []
---

# Reproduction instructions and acceptance artifacts

Commit 552aef2 supplies setup/storage/recovery instructions, environment names,
reviewed corpus cases, opt-in separate-file restart journey and read-only real
Chroma identity test. Corpus expectations were read from actual supplied pages.
The external journey requires disposable test storage, explicitly permitted
graph restart and a separately configured mocked provider endpoint; it never
silently opts into paid calls. The provider mock itself is not bundled.

The external suite is a focused tracer, not the complete deployed acceptance
matrix from the original plan. Comprehensive adversarial, reconciliation,
semantic-rewrite and target-browser behavior still need evidence. No reseeding,
re-embedding, booking fixture access or customer booking mutations occurred.

## Self-Check: SKIPPED

No pytest/JS/browser/conformance/deployed acceptance runs in this invocation,
per --no-verify. Build/start results are recorded in 01-EXECUTION.md. Phase 1
is implemented but not verified/accepted; requirement completion stays pending.

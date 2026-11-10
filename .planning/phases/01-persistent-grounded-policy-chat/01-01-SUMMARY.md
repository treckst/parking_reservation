---
phase: 01-persistent-grounded-policy-chat
plan: "01"
status: complete
subsystem: infra
tags: [sqlite, langgraph, async, testing]
provides:
  - Exact SqliteSaver async adapter with outside-graph connection lifecycle
  - Separate-file storage configuration and offline provider tests
key-files:
  created: [src/parking/checkpoint.py, src/parking/settings.py, tests/integration/test_checkpointer_conformance.py]
  modified: [pyproject.toml, uv.lock, .gitignore, .planning/PROJECT.md, .planning/config.json]
requirements-completed: []
metrics:
  tests_passed: 28
  tasks_completed: 2
---

# Plan 01-01 complete: offline prerequisites and synchronous SQLite persistence

The exact synchronous SqliteSaver 3.1.3 is wrapped by ServerSqliteAdapter. Five async operations delegate to the saver on one serialized worker; alist is an async iterator. generate_checkpointer owns a local sqlite3 connection outside the graph and drains queued work before closing it. Settings reject collisions between checkpoint, application registry and booking files. No runtime-context connection is used.

## User decisions applied

Use exactly ChatOpenAI(model="gpt-6-luna") and OpenAIEmbeddings(check_embedding_ctx_length=False). Live authentication and embedding provenance preflights were removed by explicit user instruction. Tests mock OpenAI and run without keys. Optional research/verifier/code-review subagents are disabled; execution continues inline with focused tests.

## Verification

- RED: official test_official_base_conformance executed and failed the intended passed_all_base assertion with bare synchronous SqliteSaver. Actual JUnit/JSON evidence is in 01-01-RED.xml/json; classifier returned RED_EVIDENCE_OK.
- GREEN: official five-method base conformance passes. Additional graph tests prove independent threads, history, deletion isolation, restart persistence, cancelled write draining and connection close, plus separate-file validation.
- `uv run --locked pytest -q`: 28 passed in 8.97 seconds. No live OpenAI calls.
- Exact provider constructors and mocked structured output covered by tests/unit/test_models.py.
- Docker daemon 29.7.2 is available. Image/SDK custom-hook integration is the next plan and has not yet been verified.

## Commits

- 559919f: locked dependency/runtime probes.
- b6362d8: replace removed live provider gates with mocked tests.
- 1381c85: failing async conformance baseline; lean workflow and updated project requirements.
- ff1de95: async SqliteSaver bridge, external connection lifetime and passing conformance tests.

## Deviations

Initial provider/provenance gate was removed by the user, rather than passed with live calls. Original blocked evidence remains in git history. Execution is sequential/inline with user-selected lean settings. Requirements remain unmarked until deployed behavior is demonstrated; local conformance is not claimed as deployed proof.

## Self-Check: PASSED

Required files and task commits exist. Both tasks are complete under the explicit user override; 28 local tests pass. Deployed image/SDK acceptance remains pending in Plan 01-02.

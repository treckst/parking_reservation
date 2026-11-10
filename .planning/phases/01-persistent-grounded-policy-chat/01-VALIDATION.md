---
phase: "01"
slug: "persistent-grounded-policy-chat"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-10"
---

# Phase 01 - Validation Strategy

> Execution verification contract, seeded from 01-RESEARCH.md. No application checks have run. The planner must replace provisional task bindings below with actual plan/task/wave and threat IDs before plan checking.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio, HTTPX, and langgraph-checkpoint-conformance; resolve compatible pinned dependencies during setup |
| Config file | pyproject.toml - test configuration and dependencies must be added by the initial plan |
| Quick run command | `uv run pytest tests/unit tests/integration/test_api_contract.py -q` |
| Full deterministic command | `uv run pytest -m "not deployed and not live_model" -q` |
| Saver prerequisite command | `uv run pytest tests/integration/test_checkpointer_conformance.py -q` |
| Deployed/Chroma command | `uv run pytest tests/integration/test_deployed_chat.py tests/integration/test_chroma_retrieval.py -q` |
| Configured live-model command | `uv run pytest tests/live/test_policy_cases.py -m live_model -q` |
| Runtime budget | Quick feedback target under 30 seconds; unmeasured. Container/model checks have separately bounded timeouts and may take longer. |

## Sampling Rate

- After each task, run its focused automated check; after each task commit, run the quick deterministic selection once it exists.
- After each wave, run the full deterministic suite and the external checks applicable to that wave.
- Before phase verification, run the full deterministic suite and required deployed, real-Chroma, saver/restart, and configured live-model cases.
- Every runnable automated check must name its failure condition. Non-zero exit, zero selected tests, and required skipped checks cannot establish acceptance.
- Keep no more than two consecutive tasks without automated feedback. No watch modes or indefinite retries.

## Per-Task Verification Map

Task bindings are provisional research groups. The planner must synchronize this table with the final PLAN.md tasks and security registers; no group below is a completed task.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| Saver gate - bind during planning | Initial tracer | First | GRAPH-03, GRAPH-06, DEL-02 | Bind to plan register | Exact SqliteSaver adapter, external connection, separate file, thread isolation and safe deletion | conformance/integration | `uv run pytest tests/integration/test_checkpointer_conformance.py -q` | Missing - initial plan creates | Pending |
| State/evidence - bind during planning | Policy slice | Bind during planning | GRAPH-02, GRAPH-04 | Bind to plan register | Validated state and stable query/attempt identities; no history loss or duplicate evidence | unit | `uv run pytest tests/unit/test_state.py -q` | Missing - initial plan creates | Pending |
| Policy/guards - bind during planning | Policy slice | Bind during planning | GRAPH-01, RAG-02, RAG-05, PRIV-01, PRIV-05 | Bind to plan register | Supported claims only, one silent rewrite, safe partial answers, final-only guarded output | unit | `uv run pytest tests/unit/test_policy_flow.py tests/unit/test_guards.py -q` | Missing - initial plan creates | Pending |
| API/recovery - bind during planning | Deployed chat | Bind during planning | API-01, API-05, GRAPH-03, GRAPH-06 | Bind to plan register | Ownership on every restore/recovery route; no duplicate accepted run or leaked raw state | contract/integration | `uv run pytest tests/integration/test_api_contract.py tests/integration/test_recovery.py -q` | Missing - initial plan creates | Pending |
| Real services - bind during planning | Deployed tracer | Bind during planning | RAG-07, DEL-02, DEL-04, GRAPH-03 | Bind to plan register | Compatible query embeddings, private server, healthy dependency ordering, checkpoints survive restart | deployed/integration | `uv run pytest tests/integration/test_deployed_chat.py tests/integration/test_chroma_retrieval.py -q` | Missing - initial plan creates | Pending |
| Live answers - bind during planning | Policy acceptance | Bind during planning | GRAPH-01, RAG-05, RAG-07 | Bind to plan register | English/Polish cited answers, four-facility comparison, rewrite success and final unsupported outcome | configured live model | `uv run pytest tests/live/test_policy_cases.py -m live_model -q` | Missing - initial plan creates | Pending |

## Wave 0 Requirements

- [ ] Declare test dependencies, pytest markers, isolated temporary SQLite files, and bounded external-service configuration.
- [ ] Create `tests/conftest.py` and the test files referenced in the table before invoking their checks; each must collect meaningful cases rather than empty passing stubs.
- [ ] Preserve the real booking fixture and original Chroma collection. Never import operational seed/ingestion modules or trigger accidental embedding writes from test collection.
- [ ] Establish reviewed policy/source/page expectations, including English/Polish questions, all four facilities, partial coverage, unsupported questions, and a one-rewrite-only success case.
- [ ] Mark external-service/live-model checks explicitly. Missing configuration must be reported as unverified and must not turn required deployment acceptance green.

## Mandatory Early Runtime Gates

1. Exact synchronous `SqliteSaver` has an explicitly tested async protocol bridge; conformance covers get, put, pending writes, async iteration, thread deletion, namespaces/history, thread safety, and connection lifecycle.
2. The pinned Agent Server image loads the custom hook, writes actual conversation checkpoints to the separate SQLite file, completes SDK round trips, survives restart, and continues another turn. PostgreSQL-only persistence or a local test graph does not satisfy this gate.
3. Verify model access, structured output, embedding provenance/compatibility, dependency imports, and actual service readiness. An unavailable prerequisite produces a clear execution gate rather than a silent substitute.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser close/reopen versus refresh and restored tabs | GRAPH-03; D-05, D-06 | Browser session restoration has platform-specific behavior that sessionStorage alone cannot establish | Test the target browser with restore enabled/disabled; refresh keeps the current thread, reopened browser starts fresh, stored checkpoints remain. Record any unresolved limitation instead of declaring full compliance. |
| New/duplicated tabs, New chat, pending draft and Retry | GRAPH-03, GRAPH-06, API-01; D-07, D-08, D-20-D-22 | Verify actual browser-visible behavior and network recovery alongside automated API checks | Open/duplicate tabs, refresh while a request is accepted, disconnect/reconnect, and use New chat. Confirm isolation, draft retention, disabled Send, and recovery without resubmission. |
| Inline citations, concise friendly language and final-only output | RAG-05, PRIV-05; D-01-D-04, D-13-D-19 | Semantic and visual review complements deterministic tests | Review English/Polish supported, partial, comparison, rewrite, and unsupported cases. Inspect that internal events/progress and unguarded tokens never appear. |

## Validation Sign-Off

- [ ] Final plan/task/wave and threat bindings replace provisional groups.
- [ ] Every task has an automated check or explicit initial-test-infrastructure dependency.
- [ ] All referenced test files are created before use, with meaningful collected cases.
- [ ] Sampling continuity and bounded timeouts are specified without watch modes.
- [ ] Saver conformance, deployed SDK/restart, and real-Chroma checks are mandatory before dependent expansion.
- [ ] Required live/deployed skips remain unverified; results are recorded accurately.
- [ ] `nyquist_compliant: true` is set only through the appropriate validation workflow with supporting evidence.

**Approval:** Pending execution/validation evidence; this is the planning-stage contract.

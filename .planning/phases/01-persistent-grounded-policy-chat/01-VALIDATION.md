---
phase: "01"
slug: "persistent-grounded-policy-chat"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-10"
---

# Phase 01 - Validation Strategy

> Execution verification contract synchronized with 01-01 through 01-08 PLAN files. No application checks have run; status remains draft, nyquist_compliant false and wave_0_complete false.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio, HTTPX, and langgraph-checkpoint-conformance; resolve compatible pinned dependencies during setup |
| Config file | pyproject.toml - test configuration and dependencies must be added by the initial plan |
| Quick run command | `uv run pytest tests/unit tests/integration/test_api_contract.py -m "not deployed and not live_model" -q` |
| Full deterministic command | `uv run pytest -m "not deployed and not live_model" -q` |
| Saver prerequisite command | `uv run pytest tests/integration/test_checkpointer_conformance.py -q` |
| Deployed command | `uv run pytest tests/integration/test_deployed_chat.py tests/integration/test_deployed_state.py tests/integration/test_recovery.py tests/integration/test_api_contract.py -m deployed --require-external -q` |
| Real Chroma command | `uv run pytest tests/integration/test_chroma_retrieval.py --require-external -q` |
| Configured live-model command | `uv run pytest tests/live/test_policy_cases.py -m live_model --require-external -q` |
| Browser controller command | `node --test tests/web/chat.test.mjs` |
| Runtime budget | Quick feedback target under 30 seconds; unmeasured. Container/model checks have separately bounded timeouts and may take longer. |

## Sampling Rate

- After each task, run its focused automated check; after each task commit, run the quick deterministic selection once it exists.
- After each wave, run the full deterministic suite and the external checks applicable to that wave.
- Before phase verification, run the full deterministic suite and required deployed, real-Chroma, saver/restart, and configured live-model cases.
- Every runnable automated check must name its failure condition. Non-zero exit, zero selected tests, and required skipped checks cannot establish acceptance.
- Keep no more than two consecutive tasks without automated feedback. No watch modes or indefinite retries.

## Per-Task Verification Map

Actual plan bindings below cover all 16 tasks. All checks remain pending; task files are planned, not present yet. T-01-SC applies across the phase in addition to listed specific threats.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01-01 | 1 | GRAPH-01, RAG-07 | T-01-01 | Exact model/import/provenance; no asset writes | runtime/live | `uv run pytest tests/integration/test_runtime_prerequisites.py -m "not live_model" -q`<br>`uv run pytest tests/integration/test_runtime_prerequisites.py -m live_model --require-external -q` | Missing — this task creates/extends | Pending |
| 01-01-02 | 01-01 | 1 | GRAPH-03, DEL-02 | T-01-02 | Exact saver lifecycle/isolation/conformance | conformance | `uv run pytest tests/integration/test_checkpointer_conformance.py -q` | Missing — this task creates/extends | Pending |
| 01-02-01 | 01-02 | 2 | GRAPH-01, GRAPH-03, RAG-02, RAG-07, DEL-02, DEL-04 | T-01-03, T-01-04 | Private image, real Chroma, separate-file SDK/restart | deployed | `uv run pytest tests/integration/test_deployed_chat.py -m deployed --require-external -q` | Missing — this task creates/extends | Pending |
| 01-02-02 | 01-02 | 2 | API-01, API-05, PRIV-01, PRIV-05 | T-01-03, T-01-04 | Owned safe browser/API/SDK tracer | contract/deployed | `uv run pytest tests/integration/test_deployed_chat.py -m "not deployed" -q`<br>`uv run pytest tests/integration/test_deployed_chat.py -m deployed --require-external -q` | Missing — this task extends tracer tests | Pending |
| 01-03-01 | 01-03 | 3 | GRAPH-02, GRAPH-03, GRAPH-04 | T-01-05 | Immutable query/evidence/draft retention | unit/deployed | `uv run pytest tests/unit/test_state.py -q`<br>`uv run pytest tests/integration/test_deployed_state.py -m deployed --require-external -q` | Missing — this task creates/extends | Pending |
| 01-03-02 | 01-03 | 3 | GRAPH-02, RAG-02 | T-01-05 | Current evidence and typed contextual routing | unit | `uv run pytest tests/unit/test_policy_context.py tests/unit/test_state.py -q` | Missing — this task creates/extends | Pending |
| 01-04-01 | 01-04 | 4 | RAG-05, RAG-07 | T-01-06 | Cited bilingual partial/four-facility support | unit | `uv run pytest tests/unit/test_policy_flow.py -q` | Missing — this task creates/extends | Pending |
| 01-04-02 | 01-04 | 4 | GRAPH-04, RAG-05 | T-01-07 | Single silent rewrite; same identity; explicit outage | unit | `uv run pytest tests/unit/test_policy_flow.py tests/unit/test_state.py -q` | Missing — this task creates/extends | Pending |
| 01-05-01 | 01-05 | 5 | PRIV-01 | T-01-08 | User/document injection blocked structurally | adversarial unit | `uv run pytest tests/unit/test_guards.py -k input -q` | Missing — this task creates/extends | Pending |
| 01-05-02 | 01-05 | 5 | PRIV-05, API-05 | T-01-09 | Final guard alone publishes; safe DTO/errors | unit/contract | `uv run pytest tests/unit/test_guards.py tests/integration/test_api_contract.py -m "not deployed" -q` | Missing — this task creates/extends | Pending |
| 01-06-01 | 01-06 | 3 | GRAPH-03, GRAPH-04, GRAPH-06 | T-01-10, T-01-11 | Lost-ack reconciliation; no duplicate run | recovery/deployed | `uv run pytest tests/integration/test_recovery.py -m "not deployed" -q`<br>`uv run pytest tests/integration/test_recovery.py -m deployed --require-external -q` | Missing — this task creates/extends | Pending |
| 01-06-02 | 01-06 | 3 | API-01, API-05, PRIV-01 | T-01-10, T-01-12 | Owned helpers; bounded Unicode; safe retry statuses | contract/recovery | `uv run pytest tests/integration/test_api_contract.py tests/integration/test_recovery.py -m "not deployed" -q` | Missing — this task creates/extends | Pending |
| 01-07-01 | 01-07 | 4 | GRAPH-03, API-01 | T-01-13 | Refresh/tab isolation/New chat; D-06 browser gate | JS/contract/browser | `node --test tests/web/chat.test.mjs`<br>`uv run pytest tests/integration/test_browser_contract.py -q` | Missing — this task creates/extends | Pending |
| 01-07-02 | 01-07 | 4 | GRAPH-06, API-01, API-05 | T-01-13 | Editable pending draft, final-only and recovery | JS/browser | `node --test tests/web/chat.test.mjs` | Missing — this task creates/extends | Pending |
| 01-08-01 | 01-08 | 6 | GRAPH-01, RAG-05, RAG-07 | T-01-14 | Reviewed read-only real corpus/live responses | Chroma/live | `uv run pytest tests/integration/test_chroma_retrieval.py --require-external -q`<br>`uv run pytest tests/live/test_policy_cases.py -m live_model --require-external -q` | Missing — this task creates/extends | Pending |
| 01-08-02 | 01-08 | 6 | All 14 Phase 1 IDs | T-01-01–T-01-14 | Full required restart/recovery/privacy/browser evidence | full/deployed/browser | `uv run pytest -m "not deployed and not live_model" -q`<br>`node --test tests/web/chat.test.mjs`<br>`uv run pytest tests/integration/test_deployed_chat.py tests/integration/test_deployed_state.py tests/integration/test_recovery.py tests/integration/test_api_contract.py -m deployed --require-external -q` | Missing — this task creates/extends | Pending |

Initial HTTP/DTO/ownership tracer checks live in test_deployed_chat.py (01-02); the full independent API matrix is created in 01-06-02 before later privacy/final checks use it. Final 01-08 integrated assertions extend only test_deployed_chat.py and rerun existing recovery/browser suites without changing their ownership or mandatory checks.

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

- [x] Final plan/task/wave and threat bindings replace provisional groups (planning-only synchronization, not execution evidence).
- [ ] Every task has an automated check or explicit initial-test-infrastructure dependency.
- [ ] All referenced test files are created before use, with meaningful collected cases.
- [ ] Sampling continuity and bounded timeouts are specified without watch modes.
- [ ] Saver conformance, deployed SDK/restart, and real-Chroma checks are mandatory before dependent expansion.
- [ ] Required live/deployed skips remain unverified; results are recorded accurately.
- [ ] `nyquist_compliant: true` is set only through the appropriate validation workflow with supporting evidence.

**Approval:** Pending execution/validation evidence; this is the planning-stage contract.

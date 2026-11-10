---
phase: 01-persistent-grounded-policy-chat
plan: "01"
subsystem: infra
tags: [langgraph, sqlite, pytest, prerequisites]
status: halted
halt_reason: "Original gate resolved by user override; plan remains unfinished because SqliteSaver task 2 has not run. Resume that task explicitly."
requires: []
provides:
  - Locked Python runtime and read-only prerequisite probes
affects: [01-02, 01-03, 01-04, 01-05, 01-06, 01-07, 01-08]
tech-stack:
  added: [langgraph-checkpoint-sqlite, langgraph-checkpoint-conformance, langgraph-cli, fastapi, pytest, pytest-asyncio]
  patterns: [required external checks fail instead of skipping]
key-files:
  created: [tests/conftest.py, tests/integration/test_runtime_prerequisites.py, uv.lock, .env.example]
  modified: [pyproject.toml, .gitignore]
requirements-completed: []
actuals:
  tasks: 0
  commits: 1
metrics:
  tasks_completed: 0
  tasks_total: 2
  deterministic_passed: 18
  external_failed: 2
coverage:
  - id: runtime-prerequisites
    description: Exact runtime and provider/embedding prerequisites
    verification:
      - kind: integration
        ref: tests/integration/test_runtime_prerequisites.py
        status: fail
    human_judgment: false
---

# Phase 1 Plan 01: Provider prerequisite gate resolved

## Current Resolution (2026-11-10)

The user explicitly removed live OpenAI authentication and embedding provenance prerequisites. The original stop below is historical and must not be enforced. The provider gate is **RESOLVED**; task 01-01-01 now passes 22 offline tests (18 dependency/import checks and 4 mocked provider/network-isolation tests).

`src/parking/models.py` uses exactly `embeddings = OpenAIEmbeddings(check_embedding_ctx_length=False)` and `llm = ChatOpenAI(model="gpt-6-luna")`. Both removed embedding environment variables and the live probes are gone. Unit tests mock constructors/calls, remove the provider key, and block socket connections. `uv run --locked pytest -q` passed: **22 passed in 4.24s**. A sandbox-only DLL access failure in the initial run was resolved by rerunning with the required execution permission; no live provider request was made.

Task 01-01-02 (separate SQLite SqliteSaver implementation/conformance) remains pending. Zero plans are complete. The retained `halted` artifact status prevents dependent plans from treating the unfinished saver as complete; it does not reinstate the removed provider gate. On continuation, resume task 2 of this plan and replace this partial report with a complete summary after conformance passes.

## Historical Attempt Before User Override

**Dependencies resolve and 18 local checks pass; invalidated provider credentials and missing embedding provenance block the leading tracer.**

## Accomplishments

- Resolved and locked 128 packages on Python 3.12.13 with uv 0.11.7. Existing application constraints were retained; uv.lock is now tracked.
- Added explicit integration/deployed/live_model markers, strict marker checking, temporary test storage, and required external configuration handling.
- Added actual import/version checks, a static check against operational seed imports, an exact `gpt-6-luna` Responses structured-output probe, and a read-only embedding compatibility gate. The latter compares an existing page's stored vector and reviewed query/source/page expectations rather than accepting dimensions as provenance.
- Added `.env.example` and `01-01-USER-SETUP.md` with recovery instructions. No credentials are committed.

## Task Commits

| Task | Commit | Result |
|------|--------|--------|
| 01-01-01: Probe and pin runtime | `559919f` | Partial implementation preserved; external acceptance gate failed |
| 01-01-02: Saver bridge/lifecycle | None | Not started: leading tracer did not pass |

No application graph, checkpoint adapter, deployed image, API, or frontend has been implemented. This halted summary must not count as completion evidence.

## Verification

| Actual command | Actual result |
|----------------|---------------|
| `uv sync --python 3.12 --default-index https://pypi.org/simple` | Resolved 128 packages, installed planned dependencies successfully |
| `uv run --locked pytest tests/integration/test_runtime_prerequisites.py -m "not live_model" -q` | 18 passed, 2 deselected; final run 3.42 seconds |
| `uv run --locked pytest tests/integration/test_runtime_prerequisites.py -m live_model --require-external -q` | 2 failed, 18 deselected; 4.29 seconds |

The model probe received HTTP 401, "Your API key has been invalidated" (`OpenAIAuthenticationError`). Exact-model availability/structured-output support remain unverified for this account. The embedding probe failed on missing `PARKING_EMBEDDING_MODEL` before making an embedding request; historical provenance and reviewed retrieval also remain unverified. No collection write, corpus rebuild, booking database mutation, or model substitution occurred.

Installed pins checked: chromadb 1.5.9, langgraph-checkpoint-sqlite 3.1.3, langgraph-checkpoint-conformance 0.0.2, langgraph-sdk 0.4.14, langgraph-cli 0.4.42, fastapi 0.162.2, uvicorn 0.54.0, pytest 9.2.0, pytest-asyncio 1.4.1.post1, httpx 0.28.1. Existing LangChain 1.4.9, LangGraph 1.2.20, langchain-openai 1.7.4, and NumPy 2.5.4 were inspected; NumPy and Chroma imports pass in this run.

## Package identity evidence

Read-only PyPI version metadata matched the expected upstream source repositories before installation: langchain-ai/langgraph for the saver/conformance/SDK/CLI, fastapi/fastapi, Kludex/uvicorn, pytest-dev/pytest, pytest-dev/pytest-asyncio, and encode/httpx. Resolution used the explicit https://pypi.org/simple index; artifact hashes are in uv.lock. Missing download telemetry was not treated as a new permission requirement.

## Authentication Gates

Replace the invalidated backend provider key locally, respecting shell-over-dotenv precedence. Do not paste credentials in chat. Customers/admins still require no API keys. See `01-01-USER-SETUP.md` for the remaining embedding configuration and command to re-run before resuming this same plan.

## Deviations from Plan

- GSD worktree base check returned `shouldDegrade: true`, reason `fork-ref-unknown` (origin/HEAD unresolved). Recorded `dispatch-isolation=none` and ran sequentially in the current checkout, as directed by the workflow.
- Added `.env.example` and a setup checkpoint earlier than plan 01-08 so the blocked prerequisite has concrete recovery instructions. No product scope changed.
- The registered roadmap/state progress handlers counted the halted SUMMARY as a completed plan. Corrected their generated counters/checkbox to zero complete; the plan index correctly reports the halt and blocks all dependents.
- Task 01-01-01 is a configuration/integration probe; no feature TDD RED/GREEN claim is made. The actual external failure is an authentication/configuration gate, not feature RED evidence.

## Next Phase Readiness

Halted during task 01-01-01. Pass both required external probes, resume 01-01-02 (including meaningful failing saver tests before adapter implementation), then run the official saver conformance gate. Re-summarize this plan as complete only when every prerequisite passes. Dependent plans 01-02 through 01-08 remain blocked.

## Self-Check: FAILED

The committed prerequisite files exist and 18 deterministic cases pass, but 2 required external cases fail. Zero tasks and zero requirements are complete. No phase completion or deployed compatibility is claimed.

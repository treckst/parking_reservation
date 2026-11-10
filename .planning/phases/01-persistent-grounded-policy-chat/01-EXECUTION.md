---
phase: 01-persistent-grounded-policy-chat
status: implemented_unverified
date: 2026-11-10
invocation: "1 --yolo --skip-gates --no-verify"
verification: skipped-by-user
deployment: started
---

# Phase 1 execution record

Implementation and test artifacts for Plans 01-02 through 01-08 are committed.
The user explicitly bypassed workflow gates and verification for this invocation.
No pytest, node:test, browser walkthrough, live model request, semantic retrieval
acceptance or deployed request/restart acceptance suite was run. The previous
28 passing tests cover only the restored Plan 01-01 baseline.

## Build and startup results

- `uv run langgraph build -t parking-graph:phase01 --progress plain` with
  `PYTHONUTF8=1`: final build exited 0. Base API is 0.17.1, base digest
  `sha256:38a5667c193e1b8540650cfa5c1329632e8f443c9ab2d714cf257b4a0804328d`.
- Final application image manifest list:
  `sha256:84e263405dfc50f03f534e1399d3adbaa94ca9b6ff6431f34bf7357a87b63f1f`.
  Image tag: `parking-graph:phase01`.
- `docker compose -f docker/compose.yaml up -d --wait --wait-timeout 90 graph`:
  exited 0; Chroma, PostgreSQL, Redis and graph reported healthy.
- Graph startup logs report API 0.17.1, graph module
  `parking.graph.graph`, and application startup completion in 5.531 seconds.
- Host API was launched with uvicorn on `127.0.0.1:8080` in a hidden background
  process. Its startup log reports application startup complete. Launcher PID
  was 6256; uvicorn reported PID 35232. Logs are in ignored `.runtime/api.*.log`.
- No user chat was sent. Startup/readiness is not proof of model access, live
  corpus accuracy, customer journey or separate-file restart retention.

## Startup fixes

The Chroma image has Bash but no Python/curl/wget. Its readiness check now sends
an HTTP request to `/api/v2/heartbeat` using Bash and requires HTTP 200. Existing
`chroma_data` was retained; no volume was deleted, reseeded or re-embedded.

Windows CLI file-path rewriting initially embedded backslashes in Linux hook
paths. Deployment config now uses `parking.graph.graph:graph` for the graph and
the server loader's dotted reference `parking.checkpoint.generate_checkpointer`
for the custom hook. A colon-based module reference is not supported by this
version's checkpointer loader. Startup fixes are in d1794d1 and aa7b4f2.

No entitlement prerequisite was enforced after the user's override. The actual
server started using the existing local configuration. No credentials were
created, replaced, copied into git or printed, and no additional key was needed
to complete this observed startup. This supersedes the earlier assumed blocker
recorded in 01-02-CHECKPOINT.md.

## Implementation

- Typed policy-only graph, one bounded semantic rewrite, structured judge,
  current-query evidence selection, immutable evidence reducer and final guard.
- Existing Chroma collection with approved sources and public title/page citations.
- Exact requested LangChain constructors and existing synchronous SqliteSaver
  adapter; server-managed custom hook with an outside-graph connection.
- Owned SDK-only API with durable submission fingerprints, contention control,
  paginated lost-ack reconciliation and safe response/conversation projections.
- Accessible per-tab chat, New chat, editable pending draft, safe text rendering,
  accepted-request recovery and Retry only for proven failures.
- Python/JS test artifacts, reviewed PDF cases and reproduction instructions.

## Acceptance debt

No requirement is newly marked passed. Phase 1 remains unverified, rather than
advancing to Phase 2. Important remaining evidence includes deployed custom
saver write/read/restart, remote reconciliation and crash/race matrices, RAG
quality, adversarial privacy and the actual target-browser matrix. The provided
external tracer is not the complete original acceptance matrix and requires a
separately configured mocked provider endpoint.

Strict browser-close freshness (D-06) is not established when the browser restores
session storage/cookies. Without Web Locks, the fallback starts a new thread on
load, so refresh continuity is not established on those browsers. These are
documented limits, not silently weakened requirements.

Next verification command, only when the user wants verification:
`$gsd-verify-work 1`.

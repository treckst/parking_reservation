---
status: complete
date: 2026-11-10
---

# Hybrid retrieval, tracing and API/UI deployment

Implemented LangChain EnsembleRetriever with BM25/dense weights [0.4, 0.6],
stable source/page deduplication and the same approved per-facility/shared-policy
scope on both branches. Keyword indexes are built from existing Chroma text,
cached per scope, and refreshed on graph restart. No corpus writes/re-embedding.
Added explicit langchain-classic and rank-bm25 dependencies and package/UI data
configuration. LangChain community emits a deprecation warning for its BM25
integration; the existing supported dependency is retained.

Compose now interpolates LANGSMITH_TRACING (default true), LANGSMITH_API_KEY,
LANGSMITH_PROJECT and LANGSMITH_ENDPOINT from the shell/root .env. No credentials
are embedded in Dockerfiles or source. A presence-only container check returned
tracing=true and langsmith_key_configured=true; the key was never displayed.

API has its own image/container and serves the REST endpoints and existing UI.
It derives from the built graph image to share installed dependencies, replaces
the entrypoint with Uvicorn, and copies current application/static source.
Uvicorn binds 0.0.0.0:8080 inside the container; Compose publishes only host
127.0.0.1:8080. The API uses graph:8000 and starts after graph is healthy.
The registry preserves .runtime/application.sqlite3 through a bind mount.
Health requests do not allocate owner records.

## Verification and deployment

- Focused pytest: 13 passed (hybrid ranking/deduplication/scope, API boundaries,
  health and UI assets). No provider calls.
- `node --test tests/web/chat.test.mjs`: 3 passed.
- Updated graph image built successfully using langgraph CLI, API 0.17.1.
- Final API image built successfully from that runtime. An initial separate
  Python image build was superseded to avoid duplicated full-stack downloads.
- Compose reports all five services healthy: chromadb, postgres, redis, graph, api.
- The previous host API PID 35232 occupied port 8080; stopped that task-owned
  process and replaced it with the API container at the same URL.
- Actual HTTP checks: /health, /, /app.mjs, /styles.css returned 200; POST
  /api/threads returned 200 through the remote SDK. No chat/model call was sent.
- Graph image manifest list:
  sha256:fbdc8cbde8ae1b77809665b7229f298d2268a783a90974d7e5bef6b565953e59.
- API image manifest list:
  sha256:a546cd1327d54fb073d0972e6ea9da5e0d7442520ad53419918f9811500f219f.

README and .env.example document root --env-file usage, graph-first image build,
container binding, tracing variables, hybrid scope and cache refresh.
The broader Phase 1 RAG/model/browser acceptance debt is unchanged; this quick
task does not claim end-to-end model quality or confirmed LangSmith trace delivery.

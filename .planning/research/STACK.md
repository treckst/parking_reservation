# Stack Research

**Project:** Parking Reservation Assistant
**Domain:** Local conversational parking reservations with administrator approval
**Researched:** 2026-11-10 (Europe/Warsaw)
**Confidence:** MEDIUM overall; account entitlements and historical embedding provenance remain unverified.

## Recommendation

Keep Python 3.12, uv, LangChain/LangGraph, Chroma 1.5.9, and the existing SQLite fixture. Add SQLAlchemy, FastAPI, `langgraph-sdk`, the LangGraph CLI, pytest, and a plain HTML/CSS/JavaScript frontend. Deploy the graph in its own Agent Server image before wiring FastAPI chat through the SDK. PostgreSQL holds graph-server resources; SQLite remains the booking authority. Redis supports Agent Server communication. These choices preserve the agreed architecture without introducing another agent framework or a JavaScript build system.

All externally verified findings below use MEDIUM confidence, the result returned by `gsd_run query classify-confidence --provider websearch --verified`. Recommendations are engineering judgments grounded in the project requirements and linked primary sources. Context7 MCP and its `ctx7` CLI were unavailable; official documentation and PyPI were the fallback. Published versions and declared compatibility were verified; no clean dependency resolution, container build, credential inspection, or paid model call was performed.

## Recommended Stack

### Core Technologies

| Technology | Verified baseline | Purpose | Why Recommended |
|------------|-------------------|---------|-----------------|
| CPython | 3.12.x | Application and graph runtime | Matches the repository and a documented Agent Server Python target; keep one minor version across development and containers. |
| LangChain / core | 1.4.9 / 1.7.7 | Model integration, messages, documents and schemas | Existing investment; use explicit graph nodes rather than an autonomous SQL agent. |
| LangGraph | 1.2.20 | Typed state, conditional routing, parallel retrieval, reducers and thread persistence | Direct fit for the required workflow and per-query evidence reducer. |
| `langchain-openai` | 1.7.4 | Chat model and OpenAI embeddings | Supports the Responses API and native structured output through LangChain. |
| OpenAI application model | Exact API ID `gpt-6-luna` | Intent classification, evidence assessment, booking extraction and replies | Official model page and changelog independently establish this ID; account access still requires a setup check. |
| Pydantic | 2.14.3 | Graph boundaries, model output and REST schemas | One schema system for validation and safe response projections. |
| SQLAlchemy | 2.1.8 | Small synchronous SQLite repository | Parameterized statements and explicit transactions without exposing SQL generation to the LLM. |
| SQLite | Python's bundled engine; record actual engine version | Operational booking storage | Preserves fixtures and works for this single-host demo; no separate booking database service. |
| FastAPI / Uvicorn | 0.162.2 / 0.54.0 | Customer/admin REST boundary and static frontend | Pydantic integration, ordinary HTTP endpoints and minimal serving dependencies. |
| `langgraph-sdk` | 0.4.14 | FastAPI-to-Agent-Server client | Keeps deployed chat on the required remote graph path. |
| Chroma / `langchain-chroma` | 1.5.9 / 1.1.0 | Existing policy corpus and retrieval | Keep client and existing server image aligned; preserve collection/source IDs. |
| Browser HTML, CSS, JavaScript | Platform APIs; no npm dependencies | Chat, interval selector, slot grid and separate admin panel | Forty-eight spots and three simple views do not require React, Next.js or a design system. |

Version sources: official PyPI JSON for [LangChain](https://pypi.org/pypi/langchain/json), [core](https://pypi.org/pypi/langchain-core/json), [LangGraph](https://pypi.org/pypi/langgraph/json), [OpenAI integration](https://pypi.org/pypi/langchain-openai/json), [Pydantic](https://pypi.org/pypi/pydantic/json), [SQLAlchemy](https://pypi.org/pypi/SQLAlchemy/json), [FastAPI](https://pypi.org/pypi/fastapi/json), [Uvicorn](https://pypi.org/pypi/uvicorn/json), [SDK](https://pypi.org/pypi/langgraph-sdk/json), [Chroma](https://pypi.org/pypi/chromadb/json), and [Chroma integration](https://pypi.org/pypi/langchain-chroma/json). Accessed 2026-11-10; MEDIUM.

### Supporting Libraries and Tools

| Technology | Verified version / choice | Purpose and limits |
|------------|--------------------------|--------------------|
| `langgraph-cli[inmem]` | 0.4.42 | Image build and local server tooling; keep in development/deployment dependencies. Its in-memory extra adds runtime packages. [PyPI](https://pypi.org/pypi/langgraph-cli/json). |
| pytest / HTTPX | 9.2.0 / 0.28.1 | Deterministic tests and FastAPI TestClient; mock model/SDK calls in default tests. [pytest](https://pypi.org/pypi/pytest/json), [HTTPX](https://pypi.org/pypi/httpx/json). |
| `python-dotenv` | 1.2.4 | Local development configuration only; containers receive runtime environment variables. [PyPI](https://pypi.org/pypi/python-dotenv/json). |
| `langchain-community`, `pypdf`, ReportLab | Retain ingestion dependencies; resolve/pin ReportLab when regeneration is needed | Fixture/PDF tooling belongs in an optional ingestion group, not graph request handling. ReportLab is currently missing from the manifest. |
| `zoneinfo` plus IANA timezone data | Standard library; include `tzdata` where the OS lacks data | Centralize Europe/Warsaw parsing and UTC storage/comparison; Windows setup must verify the zone loads. |
| uv | Existing project package manager | Generate a reproducible lock and track it instead of relying on the currently ignored local `uv.lock`. |

Sources accessed 2026-11-10; MEDIUM. FastAPI documents [pytest/HTTPX TestClient](https://fastapi.tiangolo.com/tutorial/testing/). Serve authored static assets with [StaticFiles](https://fastapi.tiangolo.com/tutorial/static-files/); use `fetch`, ordinary forms and CSS grid, with refresh after mutations and modest polling for admin changes. Same-origin serving avoids an extra frontend service; if separated, configure explicit local origins using [CORSMiddleware](https://fastapi.tiangolo.com/tutorial/cors/). These are recommendations, not additional product requirements.

## Model and Structured Output

The public OpenAI API model is **`gpt-6-luna`**. The official catalog confirms structured outputs and function calling; the September 22 changelog records its release. A model name shown by the Codex session alone would not prove an application API identifier. Here the independent API documentation does. Preserve `APPLICATION_MODEL=gpt-6-luna`; fail clearly on unavailable access and never silently select another model. Public documentation does not establish this account's entitlement. [Model page](https://developers.openai.com/api/docs/models/gpt-6-luna), [changelog](https://developers.openai.com/api/docs/changelog), accessed 2026-11-10; MEDIUM.

Use `ChatOpenAI(model=..., use_responses_api=True)` and `with_structured_output(Schema, method="json_schema", strict=True)` for separate classifier, evidence verdict and booking-detail schemas. Make this method explicit rather than depending on library defaults. Handle refusals, incomplete responses and parsing failures with controlled graph branches. A valid JSON object does not prove a reservation is valid: SQL and deterministic validators retain authority. Keep graph memory authoritative rather than introducing provider-managed conversation state. [ChatOpenAI integration](https://docs.langchain.com/oss/python/integrations/chat/openai), [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), accessed 2026-11-10; MEDIUM.

## Embedding Compatibility Gate

Do not infer the embedding model from the collection's 1,536 dimensions. OpenAI documents multiple models capable of that length. Local installed `langchain_openai/embeddings/base.py` currently defaults to `text-embedding-ada-002`, making that a plausible historical candidate, **not proof of how the persisted corpus was created**. The original ingestion script leaves it unspecified and the collection lacks provenance. [OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings), accessed 2026-11-10; MEDIUM for dimensions, LOW for historical model inference.

Record and share the exact embedding model, dimensions and preprocessing between ingestion and retrieval. Check stored provenance or prior ingestion output first. If provenance cannot be established, explicitly re-embed the 36 source pages into a new versioned collection with a chosen documented model, retaining the original collection until retrieval checks pass. Do not mix same-dimension vectors from different models, and do not allow Chroma's default local embedding function to supply query vectors for this corpus. Model-changing re-ingestion is a setup decision with API cost, not an action performed by this research. [Chroma embedding functions](https://docs.trychroma.com/docs/embeddings/embedding-functions), [query API](https://docs.trychroma.com/docs/querying-collections/query-and-get), accessed 2026-11-10; MEDIUM.

## Booking Database and API Pattern

Share one repository module and the same persistent SQLite **directory** volume between graph and FastAPI. Mount the directory so any journal/WAL sidecars share the same filesystem. Use per-operation SQLAlchemy sessions, foreign-key enforcement, bounded busy handling, and a short explicit `BEGIN IMMEDIATE` transaction that rechecks interval conflicts before inserting the pending hold. Include a unique operation key for retry idempotency. Avoid network calls while holding the write transaction. This is a recommended check-and-write design: SQLite permits only one simultaneous writer; an ORM alone does not prevent overlapping intervals. [SQLite transactions](https://www.sqlite.org/lang_transaction.html), [SQLAlchemy SQLite transaction behavior](https://docs.sqlalchemy.org/en/21/dialects/sqlite.html), accessed 2026-11-10; MEDIUM.

Migrate the existing status/date constraints without deleting fixture rows. Both admin PATCH and graph tools must use the same validation and transaction implementation. Keep SQLite access synchronous and execute blocking operations off asynchronous request/event-loop paths. Test concurrency using independent connections to a temporary file database, not only a shared in-memory connection. Customer responses expose explicit safe DTOs, never arbitrary SDK state.

## Graph Image and Deployment Requirements

Create an importable package with explicit build metadata and a graph export; importing it must not seed data or call embedding APIs. The minimal deployment configuration is:

```json
{
  "python_version": "3.12",
  "dependencies": ["."],
  "graphs": {"parking": "./src/parking_assistant/graph.py:graph"}
}
```

`dependencies` points to a package **directory**, not the string `requirements.txt`; `graphs` names a compiled graph or supported factory. Build with `uv run langgraph build -c langgraph.json -t parking-graph:local`. Set configuration and secrets at runtime and keep them outside the image. Pin the validated Agent Server base image/version or digest after its build smoke test. The CLI's default remote base image can otherwise change independently of Python package pins. [Application structure](https://docs.langchain.com/langsmith/application-structure), [CLI configuration/build reference](https://docs.langchain.com/langsmith/cli), accessed 2026-11-10; MEDIUM.

| Component | Local demo recommendation | Setup responsibility |
|-----------|---------------------------|----------------------|
| Agent Server | Image built by the CLI; one local instance | Register graph ID `parking`; let server persistence manage threads/checkpoints. |
| PostgreSQL | 16.x, pinned validated patch/digest | Dedicated graph-server database and persistent volume; `DATABASE_URI`. |
| Redis | Reference baseline 6.x; validate and pin supported patched image | `REDIS_URI`; pub/sub and worker coordination, not the booking authority. |
| Chroma | Existing `chromadb/chroma:1.5.9` | Preserve volume; heartbeat readiness before graph startup. |
| FastAPI + static frontend | Separate application image/service | SDK URL uses graph service DNS; same SQLite volume and business layer. |

The official standalone guide uses PostgreSQL 16 and Redis 6. Treat these as documented reference baselines, not a claim that old unpatched image tags should be deployed. Postgres and Redis require health checks; Chroma needs an actual successful heartbeat. Compose dependencies use `condition: service_healthy`; application clients still need bounded connection retries. Use service DNS inside containers, loopback-only published demo ports, persistent Postgres/SQLite/Chroma storage, and no scale-to-zero graph host. [Standalone server guide](https://docs.langchain.com/langsmith/deploy-standalone-server), accessed 2026-11-10; MEDIUM.

### Credential and License Gate

Distinguish infrastructure/provider credentials from customer/admin authentication. The agreed demo has no customer/admin login or API keys. Server-side provider credentials and Agent Server entitlement are separate deployment prerequisites, never browser inputs.

- Model/embedding access uses server-side `OPENAI_API_KEY`.
- Current standalone prerequisites list `LANGSMITH_API_KEY`, `LANGGRAPH_CLOUD_LICENSE_KEY`, `DATABASE_URI`, `REDIS_URI`, and egress to `beacon.langchain.com` for license verification/reporting unless licensed air-gapped operation is configured.
- Current CLI guidance says `langgraph up` local development uses a LangSmith key, while production requires a license; official CLI source further says the development key needs Deployment access. Do not promise that any free tracing key is sufficient.
- There is a documentation mismatch: the standalone prerequisite list includes the license, while its Docker example omits it. Resolve this against the **pinned runtime** through a startup/entitlement smoke test before depending on full deployment. [Standalone prerequisites](https://docs.langchain.com/langsmith/deploy-standalone-server), [CLI guide](https://docs.langchain.com/langsmith/cli), [official CLI source](https://github.com/langchain-ai/langgraph/blob/main/libs/cli/langgraph_cli/cli.py), accessed 2026-11-10; MEDIUM.

If entitlement blocks startup, continue deterministic graph tests and use `langgraph dev` as a local SDK target. It uses memory/local persisted state and does not establish the final image/Postgres/Redis requirement. The local development guide itself asks for a LangSmith key; verify pinned dev-runtime requirements rather than promising completely credential-free serving. A custom FastAPI wrapper invoking an in-process graph would change the agreed deployed chat path, so it is not an automatic fallback. [Local development/testing](https://docs.langchain.com/langsmith/local-dev-testing), accessed 2026-11-10; MEDIUM.

## Installation and Version Compatibility

Implementation-stage starting commands, **not executed during research**:

```powershell
uv add 'langchain==1.4.9' 'langchain-core==1.7.7' 'langgraph==1.2.20' 'langchain-openai==1.7.4'
uv add 'langgraph-sdk==0.4.14' 'langchain-chroma==1.1.0' 'chromadb==1.5.9' 'pydantic==2.14.3'
uv add 'sqlalchemy==2.1.8' 'fastapi==0.162.2' 'uvicorn==0.54.0'
uv add --dev 'langgraph-cli[inmem]==0.4.42' 'pytest==9.2.0' 'httpx==0.28.1'
uv lock
uv sync --locked
uv run pytest
```

These are published candidate pins, not a tested lock. Preserve required existing dependencies while separating ingestion tools. PyPI confirms the unusual existing lower bounds are real, including `langchain>=1.4.9`, `langgraph>=1.2.20`, `langchain-openai>=1.7.4`, `pydantic>=2.14.3`, `python-dotenv>=1.2.4`, and `langsmith>=0.14.17`; do not downgrade merely because older knowledge does not recognize them. [dotenv metadata](https://pypi.org/pypi/python-dotenv/json), [LangSmith metadata](https://pypi.org/pypi/langsmith/json), accessed 2026-11-10; MEDIUM.

| Verified metadata relationship | Consequence |
|--------------------------------|-------------|
| LangChain 1.4.9 requires core >=1.7.5,<2 and LangGraph >=1.2.12,<1.3 | Proposed core/graph satisfy these declared ranges. |
| LangGraph 1.2.20 requires SDK >=0.4.6,<0.5 | Proposed SDK 0.4.14 satisfies the range. |
| `langchain-openai` 1.7.4 requires core >=1.7.5,<2 and OpenAI SDK >=2.45.0 | Let the lock resolve its SDK; do not force an older OpenAI SDK. |
| `langchain-chroma` 1.1.0 requires Chroma >=1.3.5,<2 | Existing 1.5.9 satisfies its declared range. |
| SQLAlchemy 2.1.8 requires Python >=3.11 | Python 3.12 is suitable. |

Metadata sources are the linked PyPI JSON endpoints above, accessed 2026-11-10; MEDIUM. Full transitive compatibility and wheel imports remain setup gates. In particular, reproduce/fix the known NumPy/Chroma import failure in a clean Python 3.12 environment and Linux image before assuming direct HTTP inspection proves the Python retrieval stack works.

## Alternatives Considered and What to Avoid

| Recommended | Alternative / avoid | Reason |
|-------------|---------------------|--------|
| Explicit LangGraph workflow | Additional agent frameworks, autonomous SQL agents | Conflicts with orchestration scope or weakens deterministic booking boundaries. |
| Plain static frontend | React/Next.js/design-system stack | Adds build/runtime dependencies without a v1 need; reconsider only if UI scope grows. |
| Shared SQLAlchemy booking layer | Different admin and graph SQL implementations | Risks divergent hold/overlap/status rules. |
| SQLite bookings, Postgres graph state | Migrating bookings to Postgres now | Contradicts the agreed first deployment; revisit only for a separate scaling milestone. |
| Explicit verified embedding configuration | New default model against old vectors | Equal dimensions do not establish semantic compatibility. |
| SDK over deployed Agent Server | In-process invocation as deployed chat | Violates the server/API separation requirement. |
| Server-side configuration | Customer/admin API keys or exposed provider secrets | User explicitly chose a trusted local demo without application authentication. |

## First Phase Setup Gates

1. Resolve and lock candidate packages; prove Chroma imports and HTTP retrieval in the selected runtime.
2. Verify `gpt-6-luna` account access and structured output with an explicitly configured live check; preserve the exact requested model on failure.
3. Establish embedding provenance or plan an explicit versioned re-ingestion; record model settings.
4. Build a trivial registered graph image and test pinned-runtime entitlement, PostgreSQL/Redis persistence and restart behavior before implementing the SDK-backed API.
5. Test migrated SQLite constraints and concurrent pending holds against the shared volume before integrating conversational writes.

No credentials were read and no paid APIs were called. These unresolved checks should be visible phase acceptance gates rather than hidden assumptions in later API/frontend work.

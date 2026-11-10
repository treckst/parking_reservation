# Parking Reservation Assistant

A local English-language parking chat built with LangChain, LangGraph, FastAPI,
SQLite and Chroma. The REST API serves the UI and submits requests to the graph
server through `langgraph_sdk`.

## How it works

- The assistant offers spaces and prices for City Centre (`CTR`), Riverside
  (`RIV`), Station (`STA`) and Airport (`AIR`). SQL searches always filter by
  location, and by date and space type when supplied. Exact times are required
  to check interval availability; the fixture availability flag is a snapshot.
- Reservation details are extracted into a separate structured schema before
  SQL or collection. Natural-language dates become Europe/Warsaw timestamps.
  Each field is saved independently across turns; missing or ambiguous fields
  produce follow-up questions. Required fields are space, start/end, first name,
  surname and vehicle plate.
- A complete request creates a pending hold in `booking_requests`. The compiled
  admin subgraph receives the saved draft and summary through shared state keys
  and automatically approves or rejects it. Its ToolNode rechecks SQL rules and
  atomically inserts a `confirmed` reservation and marks the request `approved`,
  or marks the request `rejected`. The parent replies from the persisted result.
- Parking rules use existing Chroma pages with BM25/dense retrieval weighted
  0.4/0.6 and source/page citations. One semantic rewrite is attempted when the
  initial evidence is insufficient. Conversation history and earlier retrieval
  evidence remain checkpointed; availability is refreshed for each search/write.
- Customer output excludes private draft fields and other customers' records.
  Admin decisions run entirely inside the parent graph, without admin HTTP
  endpoints or human approval. Cancellation is not implemented.

See [the admin subgraph](docs/admin-approval.md) for its handoff and transaction
contract. The application uses `ChatOpenAI(model="gpt-6-luna")` and
`OpenAIEmbeddings(check_embedding_ctx_length=False)`.

## Setup and start

Requirements: Python 3.12, uv, Docker Desktop/Compose, and an existing local
`.env` with these credentials:

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Chat and query embeddings |
| `LANGSMITH_API_KEY` | Agent Server authentication with the required account access |
| `LANGGRAPH_CLOUD_LICENSE_KEY` | Alternative Agent Server license, when applicable |
| `LANGSMITH_TRACING` | Optional tracing switch; Compose defaults to `true` |

The graph needs access to LangSmith authentication even when tracing is disabled.
A DNS failure, authentication timeout or invalid credential can prevent startup.
Credentials are injected at runtime and must stay out of source and image builds.

Run from the repository root:

```powershell
uv sync --dev
# Run only if the fixture database is missing:
uv run python ingested_mock_data/seed_database.py

$env:PYTHONUTF8="1"
uv run langgraph build -t parking-graph:phase01
docker compose --env-file .env -f docker/compose.yaml up -d --build --wait
```

Build the graph image first; the API image derives from it. After changing source,
repeat both build/start commands. To restart existing containers without rebuilding:

```powershell
docker compose --env-file .env -f docker/compose.yaml restart
docker compose --env-file .env -f docker/compose.yaml ps
```

Open **http://127.0.0.1:8080**. The graph server is at
`http://127.0.0.1:8123`, and Chroma at `http://127.0.0.1:8000`.
Compose waits for Chroma, PostgreSQL and Redis before starting the graph, then
waits for graph health before starting the API. This is a trusted local demo
without customer login; the published ports bind to loopback.

Startup reuses the existing `parking_documents` collection. It does not ingest
or re-embed PDFs. For a missing collection or deliberate corpus update, follow
[the fixture/ingestion instructions](ingested_mock_data/README.md), then restart
the graph to refresh cached keyword indexes. Preserve the existing Docker volumes.

## UI API

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/threads` | Create a browser-owned conversation |
| POST | `/api/chat` | Submit `thread_id`, `request_id` and `message` |
| GET | `/api/threads/{thread_id}/requests/{request_id}` | Poll a request |
| GET | `/api/threads/{thread_id}/conversation` | Restore conversation messages |
| GET | `/health` | API process health |

Replies expose `pending`, `completed` or `failed` plus a safe graph output when
complete. The gateway preserves request IDs and reconciles lost acknowledgements
without blindly starting duplicate graph runs. It reads graph state only after a
successful run and never returns raw checkpoints.

## Storage

| Data | Host location |
| --- | --- |
| Daily spaces, requests and confirmed reservations | `ingested_mock_data/parking_november_2026.sqlite3` |
| Conversation checkpoints | `.runtime/graph/checkpoints.sqlite3` |
| Browser/thread ownership and submission ledger | `.runtime/application.sqlite3` |
| Agent Server scheduling and metadata | Compose PostgreSQL volume |
| Retrieved page collection | Compose Chroma volume |

The fixture covers November 2026. The booking schema migration preserves existing
reservations while removing the seed's November 1-10-only reservation constraint.
Pending holds and confirmed bookings both prevent interval overlaps.

Run one graph server against the custom SQLite checkpoint file. The UI uses
session storage and Web Locks for tab continuity. Refresh reconnects to the saved
thread; New chat creates another thread. Browser session restoration can retain
an old conversation after reopening the browser.

## Tests

Offline tests use temporary storage and mock provider calls. Disable tracing for
the test process to avoid waiting on external trace uploads:

```powershell
$env:LANGSMITH_TRACING="false"
$env:LANGCHAIN_TRACING_V2="false"
uv run pytest -q
node --test tests/web/chat.test.mjs
```

External Chroma/deployed tests are opt-in and skip when their prerequisites are
absent. Their setup is described in `tests/integration/test_chroma_retrieval.py`
and `tests/integration/test_deployed_chat.py`. Run deployed tests only against a
disposable test deployment.

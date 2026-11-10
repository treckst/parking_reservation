# Parking Reservation Assistant

Local policy chat using LangChain, LangGraph, the Agent Server SDK, FastAPI,
Chroma, and separate SQLite files. Live availability, booking writes and admin
actions belong to later phases. The policy graph never opens the booking DB.

## Setup

Use the project's Python 3.12 environment, uv, and Docker Compose. Copy the
names in `.env.example` into your local `.env`, preserving existing values.
Supply OpenAI and applicable Agent Server credentials locally. No customer
accounts or application API keys are used. Credentials never belong in git.

```powershell
uv sync --locked
$env:PYTHONUTF8="1"
uv run langgraph build -t parking-graph:phase01
docker compose -f docker/compose.yaml up -d chromadb postgres redis graph
uv run --env-file .env uvicorn parking.api.app:create_app --factory --app-dir src --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080. Start the API after building and starting the graph.
The API invokes only the remote SDK; it has no in-process graph fallback.
The private local Agent Server listens on loopback port 8123. Keep this local
trusted demo off public networks: its internal server has no customer login.

The graph image pins API version `0.17.1`. The base image pulled during execution
reported digest `sha256:38a5667c193e1b8540650cfa5c1329632e8f443c9ab2d714cf257b4a0804328d`;
this records the observed base, not a successful application image build.
The final application image built and Compose started all services; details are
recorded in `.planning/phases/01-persistent-grounded-policy-chat/01-EXECUTION.md`.
Runtime dependencies are declared in
`pyproject.toml` with the existing lock. Container addresses are `chromadb:8000`,
`postgres:5432` and `redis:6379`. Compose waits for their health checks. The
existing `chroma_data` volume is preserved. Do not delete/reseed it or regenerate
embeddings as part of starting the app. If that volume is empty, follow the
existing ingestion instructions separately; startup does not populate it.

The exact clients remain `ChatOpenAI(model="gpt-6-luna")` and
`OpenAIEmbeddings(check_embedding_ctx_length=False)`. No startup provider or
embedding-provenance probe runs. Provider/configuration failures are service
failures; they never cause model substitution or a semantic retrieval retry.

## Storage and recovery

Graph checkpoints use the exact synchronous `SqliteSaver`, with an asynchronous
serialized adapter loaded through `langgraph.json`'s server lifecycle hook.
The local connection is created outside graph nodes and closed after worker
drain. Compose mounts the whole `.runtime/graph` directory at `/state`, including
SQLite journals, and uses `/state/checkpoints.sqlite3`. PostgreSQL holds Agent
Server scheduling/metadata; it does not replace the custom checkpoint file.

The host API uses `.runtime/application.sqlite3` for owner/thread bindings and
the submission ledger. Keep it separate from checkpoints and the preserved
`ingested_mock_data/parking_november_2026.sqlite3` fixture. Run one graph server
against this checkpoint file. Separate API processes can share the registry;
short SQLite transactions enforce one active request per thread.

Requests have immutable IDs and exact-message fingerprints. A lost create
acknowledgement is reconciled using paginated SDK run metadata. Unknown acceptance
remains pending and is never blindly resubmitted. If there is no matching run,
the conservative outcome remains pending; an operator may need to investigate.
Only a confirmed terminal failure enables Retry. Conversation restore uses
stored user messages and guarded final responses, never raw graph state/events.

The UI uses per-tab session storage and Web Locks to detach duplicated active
tabs. Refresh restores the thread and reconnects pending requests. New chat keeps
old server data. **Browser restoration can preserve both session storage and
cookies after closing all windows. Strict fresh-conversation-on-browser-reopen
(D-06) is not established.** Browsers without Web Locks detach on load, so refresh
continuity is also not established there. The target-browser matrix is unverified.

## Tests (written; not run in the current execution)

The latest user invocation explicitly requested `--skip-gates --no-verify`.
No passing results should be inferred for the new implementation.

```powershell
uv run pytest -m "not deployed and not live_model" -q
node --test tests/web/chat.test.mjs
```

Tests mock provider calls. The local corpus cases inspect the actual PDF pages;
they do not prove live model accuracy. An optional real Chroma check queries a
stored page vector, proving read-only source identity rather than new-question
embedding quality:

```powershell
$env:TEST_CHROMA_HOST="127.0.0.1"
uv run pytest tests/integration/test_chroma_retrieval.py --require-external -q
```

The external journey requires a disposable, separately configured graph/API,
mocked OpenAI-compatible provider endpoint (`OPENAI_BASE_URL`), and explicit
test-only environment variables: `TEST_API_URL`, `TEST_GRAPH_URL`,
`TEST_CHECKPOINT_PATH`, `TEST_PROVIDER_MOCKED=1`, `TEST_ALLOW_GRAPH_RESTART=1`.
The restart command targets the graph service in this repository's Compose file;
do not point it at a shared/non-test graph. The mocked provider must return
valid schema-specific responses and collection-compatible embedding vectors.
No fake provider is selected automatically in the application.

```powershell
uv run pytest tests/integration/test_deployed_chat.py --require-external -q
```

Missing explicitly required external settings fail with `--require-external`.
Otherwise external tests skip. A skipped check is unverified. The external
journey is not a complete acceptance matrix: contention/crash cases have local
mocked coverage, while deployed reconciliation and browser behavior still need
observed evidence. Manually check refresh, duplicate/new tabs, close/reopen with
restoration enabled/disabled, New chat, pending drafts, Retry and accepted-request
reconnection. Record actual image digest, hook startup logs and separate-file
checkpoint persistence before claiming deployment acceptance.

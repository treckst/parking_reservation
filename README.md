# Parking Reservation Assistant

Local policy and reservation chat using LangChain, LangGraph, the Agent Server SDK,
FastAPI, Chroma, and separate SQLite files. Compiled policy, reservation and admin
subgraphs preserve conversation state. The customer agent uses a bound-tool loop
to inspect/update its draft and ask for missing fields across turns. It collects details,
saves a pending SQLite reservation, then passes its ID and summary to the compiled
admin subgraph. After API review, its LLM decision runs through a ToolNode that
sets the same record to approved or rejected. The parent replies from admin_result.
See [the admin approval API](docs/admin-approval.md) for request/resume details.

Customer chat is English-only. The `check_language` node uses a strict structured
LLM decision before safety checks, intent classification, retrieval or reservation
execution. Non-English, mixed-language and unclear requests receive a fixed English
request to rephrase. Booking identifiers, names, dates and times are allowed in
English requests and details-only follow-ups. All replies and review summaries
use English; rejected turns preserve earlier evidence and booking drafts.

The classifier and reservation collector receive the full role-labelled customer
conversation from the thread checkpoint. Classification also receives the saved
draft. Collection always executes `inspect_reservation_draft` before its first
LLM call; inspection is not optional model behavior. Policy evidence and admin
tool history are separate channels, not customer conversation messages. Policy
answer generation receives current retrieved evidence rather than the entire chat.

A separate `ReservationDates` structured-output step normalizes natural-language
dates before collection, using the current Europe/Warsaw time for relative dates
and the correct seasonal offset. Customers can write "November 13, 2026 from 2pm
to 9pm". Unspecified fields survive corrections; ambiguous dates require a
follow-up. Draft tools cannot overwrite normalized dates. Missing spot IDs,
names or plates also trigger a question; a facility code alone is not a spot ID.

## Setup

Use the project's Python 3.12 environment, uv, and Docker Compose. Copy the
names in `.env.example` into your local `.env`, preserving existing values.
Supply OpenAI and applicable Agent Server credentials locally. No customer
accounts or application API keys are used. Credentials never belong in git.

```powershell
uv sync --locked
# If the fixture database is missing, create it once before starting services:
uv run python ingested_mock_data/seed_database.py
$env:PYTHONUTF8="1"
uv run langgraph build -t parking-graph:phase01
docker compose --env-file .env -f docker/compose.yaml up -d --build --wait
```

Open http://127.0.0.1:8080. Compose starts the API container after the graph is
healthy. The API container serves both REST endpoints and the existing chat UI.
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

Graph tracing is controlled by Compose environment interpolation:
`LANGSMITH_TRACING` (defaults to `true`) and `LANGSMITH_ENDPOINT`.
Agent Server supplies the `parking` agent destination. Compose clears project
destination variables and their legacy aliases for this service to prevent the
SDK's `EnvAddressError` when a project and agent address are both set.
Standalone host scripts may still use `LANGSMITH_PROJECT` in `.env`.
Export tracing/endpoint variables or set them
in the root `.env` and use `docker compose --env-file .env ...` as above. Shell
values take precedence; explicitly setting tracing to `false` disables it.
Keys stay runtime environment values, never image build arguments or source.

The graph receives `LANGSMITH_API_KEY` directly from the root `.env` through
the service's `env_file`, including when running `docker compose up -d` from
`docker/`. Agent Server requires a valid key with LangGraph Cloud access (or an
applicable `LANGGRAPH_CLOUD_LICENSE_KEY`) even if tracing is disabled. If the
graph exits with code 3 and logs `License verification failed`, check that
credential and account access. Do not add an empty `LANGSMITH_API_KEY` entry
under Compose `environment`: it overrides the credential from `env_file`.

Retrieval combines LangChain BM25 and dense Chroma retrievers using
`EnsembleRetriever(weights=[0.4, 0.6])`. Reciprocal-rank fusion deduplicates by
stable source/page identity. BM25 reads the existing approved Chroma page text;
both branches apply the same facility/shared-policy scope. The corpus is not
modified or re-embedded. Restart the graph after deliberate corpus updates to
refresh cached keyword indexes.

In `docker/api.Dockerfile`, Uvicorn imports the `create_app` factory from
`parking.api.app` and listens on `0.0.0.0:8080` inside the container. Compose
publishes it only at `127.0.0.1:8080` on the host. The graph is reached through
`http://graph:8000`, rather than the API container's localhost. For optional
host-only development the equivalent command is:
`uv run --env-file .env uvicorn parking.api.app:create_app --factory --app-dir src --host 127.0.0.1 --port 8080`.

The dedicated API image derives from `parking-graph:phase01` to share installed
dependency versions, then replaces its entrypoint with Uvicorn and copies the
current application/UI source. Build the graph first, as shown above. Runtime
graph credentials are injected by Compose and are not baked into either image.

## Storage and recovery

Graph checkpoints use the exact synchronous `SqliteSaver`, with an asynchronous
serialized adapter loaded through `langgraph.json`'s server lifecycle hook.
The local connection is created outside graph nodes and closed after worker
drain. Compose mounts the whole `.runtime/graph` directory at `/state`, including
SQLite journals, and uses `/state/checkpoints.sqlite3`. PostgreSQL holds Agent
Server scheduling/metadata; it does not replace the custom checkpoint file.

The API uses `.runtime/application.sqlite3` (mounted at `/state/application.sqlite3`)
for owner/thread bindings and
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

## Tests

The original phase execution skipped acceptance checks using `--skip-gates
--no-verify`. The hybrid/container follow-up ran its focused tests; see its
summary in `.planning/quick/`. Full phase acceptance remains separate.

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

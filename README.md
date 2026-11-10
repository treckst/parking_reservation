# Parking Reservation Assistant

A full-stack transport MVP prepared for **Xelerit's winter internship recruitment task**. The application helps a driver find a parking space, understand the parking rules, and request a reservation through a browser chat interface.

The idea is to make the last part of a journey—finding somewhere to park—easier. Instead of filling in a long form, the customer describes their visit in English. The assistant looks up spaces and prices, asks for missing details, and submits the completed request for automatic review, which is reviewed by another agent.

This is a local demonstration using fictional facilities, customers, prices, and policies. It does not connect to real parking operators or process payments.

## Demo

[Recording](./recording.mp4)

## What the application does

- **Find parking:** search four locations—City Centre (`CTR`), Riverside (`RIV`), Station (`STA`), and Airport (`AIR`)—with standard, electric, accessible, and van spaces.
- **Check availability and pricing:** look up hourly prices in PLN and check a specific start/end interval against existing bookings and pending requests.
- **Build a booking through conversation:** collect the selected space, visit times, first name, surname, and vehicle registration across multiple messages. Dates and times are normalized to `Europe/Warsaw`.
- **Review a submitted request automatically:** save a pending hold, validate the request with an administrator agent, and persist an approval or rejection. Approval creates a confirmed reservation.
- **Answer policy questions:** retrieve evidence from the supplied parking PDFs and produce answers with document/page citations.
- **Recover a conversation:** restore chat history after a page refresh and reconnect to pending requests without blindly submitting the same work again.

The supplied dataset covers **1–30 November 2026**: 48 physical spaces, 1,440 daily space records, and 720 seeded reservations for 1–10 November. All facilities use the fixture opening hours of 06:00–22:00.

## The creative feature: a booking assistant grounded in data

The AI combines two sources of information with different responsibilities:

| Source | What it answers |
| --- | --- |
| SQLite booking data | Which spaces exist, their prices, and whether a requested interval can be reserved. |
| Parking-policy PDFs indexed in Chroma | Questions about facility rules, accessibility, vehicle restrictions, charging, payments, and other policies. |

The model interprets the conversation, but booking writes go through Python validation and SQLite transactions. A pending request holds its space; approval rechecks opening hours and overlaps before inserting the confirmed booking. Availability is calculated from intervals, not the fixture's historical availability flag.

Policy retrieval combines keyword search (BM25) and embedding similarity with weights of 0.4 and 0.6. The corpus contains 12 PDFs, stored as 36 complete pages with source metadata. The policy workflow can rewrite a question and retrieve once more when its first evidence set is insufficient.

## Technology and architecture

| Layer | Technologies and purpose |
| --- | --- |
| Frontend | HTML, CSS, and vanilla JavaScript ES modules; browser `fetch` calls the API. No Node.js build step is needed to run the UI. |
| Web API | Python 3.12, FastAPI, Pydantic, and Uvicorn; serves the frontend and exposes the chat endpoints. |
| AI workflows | LangChain and LangGraph; a parent graph coordinates policy, reservation, and automatic administrator subgraphs. |
| Models | `ChatOpenAI(model="gpt-6-luna")` as configured in `src/parking/models.py`; `OpenAIEmbeddings` uses the library's default embedding model. |
| Retrieval | Chroma vector db, LangChain PDF loaders, PyPDF, and BM25/vector retrieval. |
| Application persistence | SQLite for spaces/bookings, conversation checkpoints, and the browser ownership/submission registry. |
| Agent Server runtime | PostgreSQL for runtime metadata and Redis for runtime coordination. |

The browser sends messages to FastAPI, which checks conversation ownership and forwards requests to the LangGraph Agent Server through its Python SDK. The parent graph selects the appropriate workflow:

| Subgraph | Responsibility |
| --- | --- |
| Policy | Retrieve relevant document pages, assess evidence, and compose a cited answer. |
| Reservation | Extract and validate booking fields, find spaces, ask follow-up questions, and save a submitted request as a pending hold. |
| Administrator | Check the saved draft and summary, make a structured approve/reject decision, and call the fixed persistence tool. This runs automatically; there is no separate human administrator panel. |

The frontend and API live in separate source directories but are served from the same origin. CORS allows `http://127.0.0.1:8080` and `http://localhost:8080` by default. Browser ownership cookies scope chat access; this is not a user authentication system.

## Run locally

### 1. Install the prerequisites

- Git.
- Python **3.12** and [uv](https://docs.astral.sh/uv/).
- Docker with the Compose plugin, with Docker running.
- An OpenAI API key with access to the configured chat model and embeddings.
- A LangSmith API key with the Agent Server access required by the selected runtime, or an applicable.

Model inference and PDF embedding require network access and may incur provider charges. The model identifier is fixed in [`src/parking/models.py`](src/parking/models.py); if your account cannot access it, the chat workflow will not run as configured.

### 2. Clone the repository and install Python dependencies

```sh
git clone https://github.com/treckst/parking_reservation.git
cd parking_reservation
uv sync --dev
```

Run all remaining commands from the repository root.

### 3. Create the environment file

Create a file named `.env` in the repository root and replace the placeholder values:

```dotenv
OPENAI_API_KEY=your_openai_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
```

### 4. Create the SQLite fixture

The generated database is not tracked in Git. On a fresh clone, run:

```sh
uv run python ingested_mock_data/seed_database.py
```

This creates `ingested_mock_data/parking_november_2026.sqlite3`. Existing records are preserved when the seed script is run again; it is not a database reset command.

### 5. Start Chroma and ingest the supplied PDFs

Start only Chroma first, before the application images have been built:

```sh
docker compose --env-file .env -f docker/compose.yaml up -d --wait chromadb
uv run python ingested_mock_data/seed_vector_ingest.py
```

Successful ingestion reports **36 PDF pages** in the `parking_documents` collection. The PDFs are already included, so regeneration is unnecessary. Ingestion calls the embedding API; it is needed for a fresh Chroma volume, not every startup. Repeating it updates the same page IDs but makes embedding calls again.

### 6. Build the graph image and start the application

The API Dockerfile uses the graph image as its base, so build the graph first.

**macOS/Linux shell:**

```sh
PYTHONUTF8=1 uv run langgraph build -t parking-graph:phase01
docker compose --env-file .env -f docker/compose.yaml up -d --build --wait
```

**Windows PowerShell:**

```powershell
$env:PYTHONUTF8="1"
uv run langgraph build -t parking-graph:phase01
docker compose --env-file .env -f docker/compose.yaml up -d --build --wait
```

### 7. Open the frontend

Open **http://127.0.0.1:8080**. FastAPI serves both the API and the frontend; there is no separate frontend install or development server to start.

| Service | Local address |
| --- | --- |
| Browser UI | http://127.0.0.1:8080 |
| API health check | http://127.0.0.1:8080/health |
| Graph health check | http://127.0.0.1:8123/ok |
| Chroma | http://127.0.0.1:8000 |

Try a conversation such as:

> Find a standard space at City Centre on 20 November 2026 from 10:00 to 12:00.

Select one of the returned spaces, provide fictional customer details when prompted, and confirm submission. For a policy example, ask: “What are the vehicle size rules at the Airport parking location?” Use a future date within the fixture month when testing a new reservation.

### Stop or troubleshoot

```sh
docker compose --env-file .env -f docker/compose.yaml ps
docker compose --env-file .env -f docker/compose.yaml logs --tail=100 graph api
docker compose --env-file .env -f docker/compose.yaml down
```

`down` without `-v` preserves named volumes. If policy retrieval reports a missing collection, complete step 5. Restart the graph after deliberately re-ingesting changed documents to refresh the cached keyword index:

```sh
docker compose --env-file .env -f docker/compose.yaml restart graph
```

If the graph fails its health check, inspect its logs for provider credentials, Agent Server authentication, or network errors. If the API build cannot find `parking-graph:phase01`, build that image first.

## API surface

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/threads` | Start a conversation owned by the current browser. |
| `POST` | `/api/chat` | Submit `thread_id`, `request_id`, and `message`; receive a result or pending status. |
| `GET` | `/api/threads/{thread_id}/requests/{request_id}` | Poll or recover a submitted request. |
| `GET` | `/api/threads/{thread_id}/conversation` | Retrieve the browser-owned conversation history. |
| `GET` | `/health` | Check that the API is responding. |

Booking operations are invoked through the chat workflow. There are no public reservation `PUT`, `PATCH`, or `DELETE` endpoints in this version.

## Project layout and storage

| Path | Contents |
| --- | --- |
| `src/parking/web/` | Browser chat interface. |
| `src/parking/api/` | REST routes, Agent Server gateway, ownership checks, and submission tracking. |
| `src/parking/graph/` | Parent graph, three subgraphs, structured state, prompts, and tools. |
| `src/parking/bookings.py` | SQLite availability queries and transactional reservation writes. |
| `src/parking/retrieval.py` | Policy retrieval and source metadata handling. |
| `src/parking/checkpoint.py` | SQLite conversation checkpoint adapter. |
| `ingested_mock_data/` | Fixture scripts and policy PDFs. |
| `docker/` | Compose configuration and API Dockerfile. |
| `tests/` | Python tests and browser-controller tests. |
| `AGENTS.md`, `.planning/` | Committed AI-agent guidance, plans, audits, and implementation records. |

With Compose, bookings are stored in `ingested_mock_data/parking_november_2026.sqlite3`, graph checkpoints in `.runtime/graph/checkpoints.sqlite3`, and the web API registry in `.runtime/application.sqlite3`. Chroma and PostgreSQL use named Docker volumes.

## Tests

The tests cover booking conflicts, field collection, graph state, retrieval, API ownership, and request recovery. Provider calls in the default suite are mocked; external-service checks are opt-in.

**macOS/Linux shell:**

```sh
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false uv run pytest -q
```

**Windows PowerShell:**

```powershell
$env:LANGSMITH_TRACING="false"
$env:LANGCHAIN_TRACING_V2="false"
uv run pytest -q
```

With Node.js installed, run the frontend controller tests separately:

```sh
node --test tests/web/chat.test.mjs
```

External checks under `tests/integration/` document their required environment variables and isolated test services. Passing mocked tests does not establish live model quality or successful deployment.

## AI-assisted development

Leveraged Codex with GSD skill.
The repository records an AI-agent development workflow through [AGENTS.md](AGENTS.md) and the [.planning/](.planning/) directory. These contain project constraints, implementation plans, execution summaries, and verification records for the graph, API, persistence, and frontend work. The guidance emphasizes readable code, transactional booking checks, scoped customer data, and focused tests.



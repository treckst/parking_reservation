<!-- GSD:project-start source:PROJECT.md -->

## Project

**Parking Reservation Assistant**

A local parking reservation demo for customers and administrators, built on the repository's existing SQLite fixtures and Chroma policy documents. Customers use a simple chat interface and live slot grid to ask questions, check availability and pricing, and request or cancel bookings. Administrators use a separate bookings panel and API routes to inspect reservations and approve or reject pending requests.

The reservation application, graph, API, and frontend are planned work; the current implementation provides fixture generation, document ingestion, and a Chroma service definition.

**Core Value:** Customers can request a valid parking reservation through conversation, with accurate availability, no overlapping bookings, administrator approval, and no disclosure of other customers' personal details.

### Constraints

- **Agent stack**: Use only LangChain and LangGraph for agent orchestration — explicit user requirement.
- **Application LLM**: Use the requested `gpt-6-luna`, subject to verifying its API identifier and availability — explicit user choice.
- **Storage**: Reuse existing Chroma documents and SQLite booking data; add PostgreSQL and Redis for the graph server — preserve the current assets and requested deployment shape.
- **Memory**: Preserve retrieved evidence per query in a thread using a custom reducer — later turns must not clear previous retrieval results.
- **Correctness**: Pending bookings hold slots, and reservation writes must prevent overlaps transactionally — an availability read alone cannot prevent a race.
- **Privacy**: Customer paths must not expose another customer's PII or reservations — filters must be backed by scoped data access and response schemas.
- **Access model**: No customer/admin login or API keys; use separate endpoints and UI surfaces within a local trusted demo — explicitly agreed during discovery.
- **Deployment**: Build and deploy the graph server image before the SDK-backed REST integration; use Compose readiness dependencies so Chroma is available before the graph starts.
- **Maintainability**: Prefer readable, self-explaining code without overloading it — explicit user preference.
- **Testing**: Supply pytest unit and integration coverage for SQL overlaps, REST endpoints, and RAG accuracy, including the critical state and privacy behavior.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python >=3.12, with local interpreter selection `3.12` in `.python-version`; the executable project consists of `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, and `ingested_mock_data/seed_vector_ingest.py`.
- SQL embedded in `ingested_mock_data/seed_database.py` defines SQLite tables, constraints, an index, and parameterized inserts.
- YAML in `docker/compose.yaml` defines the local Chroma service. No frontend language or implemented web application is detected in the empty `src/` directory.

## Runtime

- Python scripts run directly at module scope; `pyproject.toml` defines project `parking-reservation` version `0.1.0` and requires Python >=3.12.
- Chroma server runs in the prebuilt `chromadb/chroma:1.5.9` Docker image from `docker/compose.yaml`.
- `.codex/` contains developer-agent tooling, not application runtime implementation; do not infer application frameworks from its dependencies.
- uv is the documented workflow (`uv sync`, `uv run python ...`) in `ingested_mock_data/README.md`; its version is not pinned in `pyproject.toml`.
- `uv.lock` exists locally (lock format version 1, revision 3), but `.gitignore` excludes it. Treat `pyproject.toml` ranges as the portable dependency contract rather than assuming this local lock is distributed.
- `.venv/` exists and is ignored by `.gitignore`; installed versions were not used to claim project requirements.

## Frameworks

- LangChain integrations implement a PDF-to-vector-store pipeline in `ingested_mock_data/seed_vector_ingest.py`: `DirectoryLoader` / `PyPDFLoader`, `OpenAIEmbeddings`, and `langchain_chroma.Chroma`.
- `langchain>=1.4.9`, `langchain-core>=1.7.6`, and `langgraph>=1.2.20` are declared in `pyproject.toml`; no application agent, graph, chain orchestration, HTTP server, or chat interface is implemented in `src/`.
- `langchain-text-splitters>=1.1.3` is declared in `pyproject.toml`, but ingestion explicitly preserves whole pages and does not use a splitter in `ingested_mock_data/seed_vector_ingest.py`.
- No project test runner, test dependency group, or test configuration is declared in `pyproject.toml`; no application test files are present under `src/` or `ingested_mock_data/`.
- Ingestion performs a runtime ID-count check after writing documents in `ingested_mock_data/seed_vector_ingest.py`; this is a script assertion, not an automated test suite.
- Docker Compose provides local service orchestration in `docker/compose.yaml`; there is no application Dockerfile or application build configuration in `pyproject.toml`.
- `pyproject.toml` contains project metadata and dependencies only: no build-system table, console script entry point, lint configuration, or formatter configuration.
- ReportLab is required by `ingested_mock_data/generate_pdfs.py`, but is absent from `pyproject.toml`; `ingested_mock_data/README.md` instructs manual installation when regenerating PDFs.

## Key Dependencies

| Dependency | Declared requirement | Implemented responsibility |
|------------|----------------------|----------------------------|
| `chromadb` | `==1.5.9` | HTTP client, heartbeat and local server connection in `ingested_mock_data/seed_vector_ingest.py`; server image matches in `docker/compose.yaml`. |
| `langchain-chroma` | `>=1.0` | Chroma vector-store adapter and document upsert in `ingested_mock_data/seed_vector_ingest.py`. |
| `langchain-community` | `>=0.4` | Directory and page-level PDF loaders in `ingested_mock_data/seed_vector_ingest.py`. |
| `langchain-openai` | `>=1.7.4` | Embedding client in `ingested_mock_data/seed_vector_ingest.py`. |
| `pypdf` | `>=6.0` | PDF parser dependency for the selected `PyPDFLoader` in `ingested_mock_data/seed_vector_ingest.py`. |
| `python-dotenv` | `>=1.2.4` | Loads root environment configuration in `ingested_mock_data/seed_vector_ingest.py`. |
| `reportlab` | Not declared | Produces the reference PDFs in `ingested_mock_data/generate_pdfs.py`; version is not pinned. |
- Python standard-library `sqlite3` provides relational persistence without an ORM in `ingested_mock_data/seed_database.py`; the SQLite engine version is not pinned.
- `langsmith>=0.14.17` and `pydantic>=2.14.3` are declared in `pyproject.toml`, but no explicit tracing setup or application Pydantic model is implemented in `ingested_mock_data/` or `src/`.
- Standard-library `random`, `datetime`, and `pathlib` provide deterministic mock records, fixed-offset timestamps and script-relative paths in `ingested_mock_data/seed_database.py`.

## Configuration

- `ingested_mock_data/seed_vector_ingest.py` calls `load_dotenv(root / ".env")` and reads `OPENAI_API_KEY`; existing process environment values take precedence. `.env` exists; its contents were not inspected.
- The ingestion client hardcodes `127.0.0.1:8000`, plaintext HTTP and collection `parking_documents` in `ingested_mock_data/seed_vector_ingest.py`.
- `OpenAIEmbeddings(check_embedding_ctx_length=False)` leaves model choice to the dependency default in `ingested_mock_data/seed_vector_ingest.py`. Preserve embedding-model compatibility when adding retrieval; the repository does not pin a model name in code.
- `docker/compose.yaml` sets `CHROMA_PERSIST_PATH` to `/data` and mounts named volume `chroma_data` there.
- `ingested_mock_data/seed_database.py` fixes the dataset to November 2026 with a November 9 noon snapshot and UTC+01:00 timestamps; this is fixture configuration, not live availability logic.
- Dependency and Python requirements: `pyproject.toml`, `.python-version`, and local `uv.lock`.
- Local vector database: `docker/compose.yaml`.
- Operational instructions: `ingested_mock_data/README.md`; root `README.md` is empty.

## Platform Requirements

- Python 3.12 or newer and uv for the documented dependency workflow in `pyproject.toml` and `ingested_mock_data/README.md`.
- Docker with Compose for the Chroma service in `docker/compose.yaml`.
- A valid OpenAI API credential and outbound network access for `ingested_mock_data/seed_vector_ingest.py`; ingestion sends page text for embedding and incurs API usage on reruns.
- Only the Python standard library is needed for `ingested_mock_data/seed_database.py`; PDF regeneration additionally needs ReportLab as documented in `ingested_mock_data/README.md`.
- No production application hosting target or deploy pipeline is detected. `docker/compose.yaml` is a loopback-bound local Chroma deployment, and `src/` has no application implementation.

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Use descriptive snake_case Python script names, as in `ingested_mock_data/seed_database.py`, `ingested_mock_data/seed_vector_ingest.py`, and `ingested_mock_data/generate_pdfs.py`.
- PDF filenames use lowercase topic names and facility prefixes, such as `ingested_mock_data/pdfs/booking_policy.pdf` and `ingested_mock_data/pdfs/facility_ctr.pdf`.
- Use snake_case for project functions: `page_footer(canvas, document)` in `ingested_mock_data/generate_pdfs.py` is the only explicit function definition in the application scripts.
- Most work executes as module-level statements and loops in all three scripts; there is no established service-method or application-handler convention under the empty `src/` directory.
- Use snake_case names such as `local_timezone`, `occupied_now`, `daily_slots`, and `vector_store` in `ingested_mock_data/seed_database.py` and `ingested_mock_data/seed_vector_ingest.py`.
- Configuration-like values also use lowercase module-level variables (`snapshot`, `facilities`, `root`); uppercase Python constants are not an established convention in these scripts.
- Preserve cross-artifact facility codes (`CTR`, `RIV`, `STA`, `AIR`), spot IDs, and reservation IDs defined in `ingested_mock_data/seed_database.py` and described in `ingested_mock_data/README.md`.
- No project classes or type annotations are present in `ingested_mock_data/*.py`; data uses lists, tuples, sets, dictionaries, and library objects.
- SQLite column names are snake_case, with constrained string status/type values in `ingested_mock_data/seed_database.py`. Preserve these persisted names when extending consumers.

## Code Style

- No formatter configuration or formatter dependency is declared in `pyproject.toml`.
- Match four-space indentation, double-quoted strings, f-strings, parenthesized multiline calls, and blank lines between logical sections in `ingested_mock_data/seed_database.py`.
- Long prose strings and compact tuple rows are common in `ingested_mock_data/generate_pdfs.py`; no enforced line-length limit is detected.
- Keep SQL in triple-quoted strings and bind row values through `?` placeholders, following `ingested_mock_data/seed_database.py`.
- No application Ruff, Flake8, Pylint, mypy, pre-commit, or equivalent configuration is detected; `pyproject.toml` contains project metadata and runtime dependencies only.
- No lint command or enforced lint rules are supplied by `pyproject.toml` or `ingested_mock_data/README.md`.

## Import Organization

- Not detected. Use `Path(__file__)` to locate sibling outputs and the repository root, following all three scripts in `ingested_mock_data/`.
- Normalize PDF source metadata to repository-relative POSIX paths in `ingested_mock_data/seed_vector_ingest.py`; those paths form persisted vector-store identifiers.

## Error Handling

- Fail early with `SystemExit` for missing/mock API configuration, missing PDF pages, or blank page text in `ingested_mock_data/seed_vector_ingest.py`.
- Use an explicit exception for a failed postcondition: `ingested_mock_data/seed_vector_ingest.py` raises `RuntimeError` if Chroma returns fewer stored IDs than expected.
- Third-party loader, network, and embedding failures propagate directly in `ingested_mock_data/seed_vector_ingest.py`; no retries, wrapping, or centralized exception handler is present.
- Preserve the connection transaction context and `finally: connection.close()` in `ingested_mock_data/seed_database.py`; SQL failures propagate while connection cleanup is guaranteed.
- Keep SQLite integrity constraints with the schema in `ingested_mock_data/seed_database.py`: foreign keys, allowed statuses/types, date bounds, and timestamp ordering are enforced at persistence time.
- `ingested_mock_data/generate_pdfs.py` lets filesystem and ReportLab failures propagate without a recovery layer.

## Logging

- Print the database path and table counts after the transaction in `ingested_mock_data/seed_database.py`.
- Print ingestion count, target collection, and embedding model after verifying returned IDs in `ingested_mock_data/seed_vector_ingest.py`.
- Print each generated output path after building the PDF in `ingested_mock_data/generate_pdfs.py`.
- No structured logger, severity levels, or log configuration is established in `pyproject.toml` or `ingested_mock_data/*.py`.

## Comments

- Start scripts with a module docstring describing purpose and execution requirements, as in `ingested_mock_data/seed_database.py` and `ingested_mock_data/seed_vector_ingest.py`.
- Explain domain caveats and persistence choices: snapshot availability is distinct from interval availability in `ingested_mock_data/seed_database.py`; stable page IDs and disabled input splitting are explained in `ingested_mock_data/seed_vector_ingest.py`.
- Keep operator setup instructions and dataset boundaries in `ingested_mock_data/README.md`.
- Not applicable to the Python source in `ingested_mock_data/`. Python function docstrings are not used by `page_footer` in `ingested_mock_data/generate_pdfs.py`.

## Function Design

## Module Design

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| SQLite seed | Generate deterministic spots and reservations, create constrained tables, insert missing records | `ingested_mock_data/seed_database.py` |
| PDF generator | Define fictional facility/policy content and render twelve three-page PDFs | `ingested_mock_data/generate_pdfs.py` |
| PDF ingestion | Load pages, normalize metadata, embed pages, upsert and verify IDs | `ingested_mock_data/seed_vector_ingest.py` |
| Chroma service definition | Expose loopback HTTP service and persist vector data in a named volume | `docker/compose.yaml` |
| Fixture usage documentation | Explain snapshot semantics and explicit run commands | `ingested_mock_data/README.md` |
| Application source location | Empty directory; no implemented application responsibilities | `src/` |

## Pattern Overview

- All three scripts execute work at module scope; there is no package service layer or `main()` boundary in `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, or `ingested_mock_data/seed_vector_ingest.py`.
- Paths resolve from the script location, permitting execution from different working directories; follow this approach for fixture paths in `ingested_mock_data/seed_database.py` and `ingested_mock_data/seed_vector_ingest.py`.
- SQL uses bound parameters and conflict-preserving inserts; preserve composite identity semantics from `ingested_mock_data/seed_database.py`.
- PDF pages are the ingestion units. Do not assume a text splitter or overlapping chunks exist in `ingested_mock_data/seed_vector_ingest.py`.

## Layers

- Purpose: Construct fictional November 2026 reference data.
- Location: `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`.
- Contains: Literal facility data, deterministic random reservation generation, SQL schema, ReportLab rendering.
- Depends on: Python standard library for SQLite; ReportLab for PDFs.
- Used by: Manual script invocation documented in `ingested_mock_data/README.md`.
- Purpose: Convert PDF pages into vector records.
- Location: `ingested_mock_data/seed_vector_ingest.py`.
- Contains: DirectoryLoader/PyPDFLoader setup, metadata normalization, stable IDs, embedding and vector-store adapters.
- Depends on: `ingested_mock_data/pdfs/`, OpenAI embeddings, Chroma HTTP service.
- Used by: Manual ingestion invocation; no application retrieval caller exists in `src/`.
- Purpose: Store structured fixtures and embedded reference text independently.
- Location: `ingested_mock_data/parking_november_2026.sqlite3`, `docker/compose.yaml`.
- Contains: SQLite tables and a Docker volume for the `parking_documents` collection.
- Depends on: SQLite file access and running Chroma infrastructure, respectively.
- Used by: The two seed scripts; no live booking mutation flow is implemented in `src/`.

## Data Flow

### Primary Request Path

### SQLite Fixture Flow

### PDF Rendering Flow

- Working collections and clients are module-level variables in each script; there is no session or conversational state in `src/`.
- SQLite persistence preserves existing conflicting records on repeat runs (`ingested_mock_data/seed_database.py`).
- Chroma uses stable source/page IDs for upserts; deleted source PDFs do not cause deletion of existing vector records (`ingested_mock_data/seed_vector_ingest.py`, `ingested_mock_data/README.md`).

## Key Abstractions

- Purpose: Represent one physical spot on one date, with type, price, hours and snapshot availability.
- Examples: `transport_slots` schema in `ingested_mock_data/seed_database.py`.
- Pattern: Composite primary key `(spot_id, slot_date)`; reference both fields from reservations.
- Purpose: Represent a fictional scheduled visit and customer/vehicle details.
- Examples: `reservations` schema in `ingested_mock_data/seed_database.py`.
- Pattern: Text identifier, constrained same-day start/end, status enum, foreign key to daily slot, index on spot/start/end.
- Purpose: Preserve one entire PDF page as a retrievable document.
- Examples: `documents` and `ids` in `ingested_mock_data/seed_vector_ingest.py`.
- Pattern: LangChain document with text, source metadata, zero-based page number and stable source/page identity.

## Entry Points

- Locations: `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, `ingested_mock_data/seed_vector_ingest.py`.
- Triggers: Direct Python execution; imports also execute their module-level work.
- Responsibilities: Seed SQLite, generate PDFs and ingest vectors, respectively.
- Location: `docker/compose.yaml`.
- Trigger: Explicit Docker Compose startup.
- Responsibilities: Run Chroma 1.5.9 on host loopback port 8000 with persistent `/data` volume.

## Architectural Constraints

- **Threading:** No application-managed threads, workers, or async orchestration are implemented in the three `ingested_mock_data/*.py` scripts; calls are sequential.
- **Global state:** Random seed, data lists and database connection are module-level in `ingested_mock_data/seed_database.py`; loader, API-key variable, clients and embedding adapter are module-level in `ingested_mock_data/seed_vector_ingest.py`.
- **Circular imports:** No local-script imports or application import cycles are detected in `ingested_mock_data/*.py`; `src/` is empty.
- **Temporal scope:** Data is fixed to November 2026 with a November 9 noon UTC+01:00 snapshot. Do not treat the availability flag as an interval booking guarantee (`ingested_mock_data/seed_database.py`, `ingested_mock_data/README.md`).
- **Embedding compatibility:** Querying must use the same embedding model as ingestion; the script leaves model selection to the library default (`ingested_mock_data/seed_vector_ingest.py`).
- **Local infrastructure:** Chroma client address and collection name are literal values in `ingested_mock_data/seed_vector_ingest.py`, matching `docker/compose.yaml`.

## Anti-Patterns

### Importing executable seed modules as libraries

### Duplicating domain definitions across fixture producers

## Error Handling

- `SystemExit` explains missing/mock key, no documents or blank pages in `ingested_mock_data/seed_vector_ingest.py`.
- `RuntimeError` signals failed post-ingest ID-count verification in `ingested_mock_data/seed_vector_ingest.py`.
- Database transaction handling and `finally: connection.close()` protect connection lifecycle in `ingested_mock_data/seed_database.py`.
- PDF generation has no explicit exception recovery in `ingested_mock_data/generate_pdfs.py`.

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `$gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `$gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `$gsd-debug` for investigation and bug fixing
- `$gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `$gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

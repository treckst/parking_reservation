# Technology Stack

**Analysis Date:** 2026-11-09

## Languages

**Primary:**
- Python >=3.12, with local interpreter selection `3.12` in `.python-version`; the executable project consists of `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, and `ingested_mock_data/seed_vector_ingest.py`.

**Secondary:**
- SQL embedded in `ingested_mock_data/seed_database.py` defines SQLite tables, constraints, an index, and parameterized inserts.
- YAML in `docker/compose.yaml` defines the local Chroma service. No frontend language or implemented web application is detected in the empty `src/` directory.

## Runtime

**Environment:**
- Python scripts run directly at module scope; `pyproject.toml` defines project `parking-reservation` version `0.1.0` and requires Python >=3.12.
- Chroma server runs in the prebuilt `chromadb/chroma:1.5.9` Docker image from `docker/compose.yaml`.
- `.codex/` contains developer-agent tooling, not application runtime implementation; do not infer application frameworks from its dependencies.

**Package Manager:**
- uv is the documented workflow (`uv sync`, `uv run python ...`) in `ingested_mock_data/README.md`; its version is not pinned in `pyproject.toml`.
- `uv.lock` exists locally (lock format version 1, revision 3), but `.gitignore` excludes it. Treat `pyproject.toml` ranges as the portable dependency contract rather than assuming this local lock is distributed.
- `.venv/` exists and is ignored by `.gitignore`; installed versions were not used to claim project requirements.

## Frameworks

**Core:**
- LangChain integrations implement a PDF-to-vector-store pipeline in `ingested_mock_data/seed_vector_ingest.py`: `DirectoryLoader` / `PyPDFLoader`, `OpenAIEmbeddings`, and `langchain_chroma.Chroma`.
- `langchain>=1.4.9`, `langchain-core>=1.7.6`, and `langgraph>=1.2.20` are declared in `pyproject.toml`; no application agent, graph, chain orchestration, HTTP server, or chat interface is implemented in `src/`.
- `langchain-text-splitters>=1.1.3` is declared in `pyproject.toml`, but ingestion explicitly preserves whole pages and does not use a splitter in `ingested_mock_data/seed_vector_ingest.py`.

**Testing:**
- No project test runner, test dependency group, or test configuration is declared in `pyproject.toml`; no application test files are present under `src/` or `ingested_mock_data/`.
- Ingestion performs a runtime ID-count check after writing documents in `ingested_mock_data/seed_vector_ingest.py`; this is a script assertion, not an automated test suite.

**Build/Dev:**
- Docker Compose provides local service orchestration in `docker/compose.yaml`; there is no application Dockerfile or application build configuration in `pyproject.toml`.
- `pyproject.toml` contains project metadata and dependencies only: no build-system table, console script entry point, lint configuration, or formatter configuration.
- ReportLab is required by `ingested_mock_data/generate_pdfs.py`, but is absent from `pyproject.toml`; `ingested_mock_data/README.md` instructs manual installation when regenerating PDFs.

## Key Dependencies

**Critical:**

| Dependency | Declared requirement | Implemented responsibility |
|------------|----------------------|----------------------------|
| `chromadb` | `==1.5.9` | HTTP client, heartbeat and local server connection in `ingested_mock_data/seed_vector_ingest.py`; server image matches in `docker/compose.yaml`. |
| `langchain-chroma` | `>=1.0` | Chroma vector-store adapter and document upsert in `ingested_mock_data/seed_vector_ingest.py`. |
| `langchain-community` | `>=0.4` | Directory and page-level PDF loaders in `ingested_mock_data/seed_vector_ingest.py`. |
| `langchain-openai` | `>=1.7.4` | Embedding client in `ingested_mock_data/seed_vector_ingest.py`. |
| `pypdf` | `>=6.0` | PDF parser dependency for the selected `PyPDFLoader` in `ingested_mock_data/seed_vector_ingest.py`. |
| `python-dotenv` | `>=1.2.4` | Loads root environment configuration in `ingested_mock_data/seed_vector_ingest.py`. |
| `reportlab` | Not declared | Produces the reference PDFs in `ingested_mock_data/generate_pdfs.py`; version is not pinned. |

Declared requirements above come from `pyproject.toml`; they do not describe verified installed package versions.

**Infrastructure:**
- Python standard-library `sqlite3` provides relational persistence without an ORM in `ingested_mock_data/seed_database.py`; the SQLite engine version is not pinned.
- `langsmith>=0.14.17` and `pydantic>=2.14.3` are declared in `pyproject.toml`, but no explicit tracing setup or application Pydantic model is implemented in `ingested_mock_data/` or `src/`.
- Standard-library `random`, `datetime`, and `pathlib` provide deterministic mock records, fixed-offset timestamps and script-relative paths in `ingested_mock_data/seed_database.py`.

## Configuration

**Environment:**
- `ingested_mock_data/seed_vector_ingest.py` calls `load_dotenv(root / ".env")` and reads `OPENAI_API_KEY`; existing process environment values take precedence. `.env` exists; its contents were not inspected.
- The ingestion client hardcodes `127.0.0.1:8000`, plaintext HTTP and collection `parking_documents` in `ingested_mock_data/seed_vector_ingest.py`.
- `OpenAIEmbeddings(check_embedding_ctx_length=False)` leaves model choice to the dependency default in `ingested_mock_data/seed_vector_ingest.py`. Preserve embedding-model compatibility when adding retrieval; the repository does not pin a model name in code.
- `docker/compose.yaml` sets `CHROMA_PERSIST_PATH` to `/data` and mounts named volume `chroma_data` there.
- `ingested_mock_data/seed_database.py` fixes the dataset to November 2026 with a November 9 noon snapshot and UTC+01:00 timestamps; this is fixture configuration, not live availability logic.

**Build:**
- Dependency and Python requirements: `pyproject.toml`, `.python-version`, and local `uv.lock`.
- Local vector database: `docker/compose.yaml`.
- Operational instructions: `ingested_mock_data/README.md`; root `README.md` is empty.

## Platform Requirements

**Development:**
- Python 3.12 or newer and uv for the documented dependency workflow in `pyproject.toml` and `ingested_mock_data/README.md`.
- Docker with Compose for the Chroma service in `docker/compose.yaml`.
- A valid OpenAI API credential and outbound network access for `ingested_mock_data/seed_vector_ingest.py`; ingestion sends page text for embedding and incurs API usage on reruns.
- Only the Python standard library is needed for `ingested_mock_data/seed_database.py`; PDF regeneration additionally needs ReportLab as documented in `ingested_mock_data/README.md`.

**Production:**
- No production application hosting target or deploy pipeline is detected. `docker/compose.yaml` is a loopback-bound local Chroma deployment, and `src/` has no application implementation.

---

*Stack analysis: 2026-11-09*

<!-- refreshed: 2026-11-09 -->
# Architecture

**Analysis Date:** 2026-11-09

## System Overview

The implemented system is a set of standalone data preparation scripts, not a running reservation application. `src/` is empty. `pyproject.toml` declares an AI-oriented dependency set, but no application graph, API, UI, retrieval endpoint, or booking service is implemented there.

```text
Fixture preparation                         Document ingestion
`ingested_mock_data/seed_database.py`        `ingested_mock_data/generate_pdfs.py`
          |                                             |
          v                                             v
`ingested_mock_data/                         `ingested_mock_data/pdfs/`
 parking_november_2026.sqlite3`                          |
                                                       v
                                      `ingested_mock_data/seed_vector_ingest.py`
                                         |                         |
                                         v                         v
                                  OpenAI embeddings        Chroma HTTP server
                                                         `docker/compose.yaml`
                                                                  |
                                                                  v
                                                       Docker volume chroma_data
```

The SQLite fixture and PDF corpus are separate sources with common fictional facility identifiers. There is no implemented runtime component joining them; their intended usage is explained in `ingested_mock_data/README.md`.

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

**Overall:** Script-driven fixture preparation with independent relational and vector storage paths.

**Key Characteristics:**
- All three scripts execute work at module scope; there is no package service layer or `main()` boundary in `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, or `ingested_mock_data/seed_vector_ingest.py`.
- Paths resolve from the script location, permitting execution from different working directories; follow this approach for fixture paths in `ingested_mock_data/seed_database.py` and `ingested_mock_data/seed_vector_ingest.py`.
- SQL uses bound parameters and conflict-preserving inserts; preserve composite identity semantics from `ingested_mock_data/seed_database.py`.
- PDF pages are the ingestion units. Do not assume a text splitter or overlapping chunks exist in `ingested_mock_data/seed_vector_ingest.py`.

## Layers

**Fixture definition and generation:**
- Purpose: Construct fictional November 2026 reference data.
- Location: `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`.
- Contains: Literal facility data, deterministic random reservation generation, SQL schema, ReportLab rendering.
- Depends on: Python standard library for SQLite; ReportLab for PDFs.
- Used by: Manual script invocation documented in `ingested_mock_data/README.md`.

**Document loading and embedding:**
- Purpose: Convert PDF pages into vector records.
- Location: `ingested_mock_data/seed_vector_ingest.py`.
- Contains: DirectoryLoader/PyPDFLoader setup, metadata normalization, stable IDs, embedding and vector-store adapters.
- Depends on: `ingested_mock_data/pdfs/`, OpenAI embeddings, Chroma HTTP service.
- Used by: Manual ingestion invocation; no application retrieval caller exists in `src/`.

**Persistence:**
- Purpose: Store structured fixtures and embedded reference text independently.
- Location: `ingested_mock_data/parking_november_2026.sqlite3`, `docker/compose.yaml`.
- Contains: SQLite tables and a Docker volume for the `parking_documents` collection.
- Depends on: SQLite file access and running Chroma infrastructure, respectively.
- Used by: The two seed scripts; no live booking mutation flow is implemented in `src/`.

## Data Flow

### Primary Request Path

There is no HTTP request path in `src/`. The main external-service flow is PDF ingestion:

1. Resolve repository root, load environment configuration, reject absent/mock API keys (`ingested_mock_data/seed_vector_ingest.py:17`).
2. Load `pdfs/**/*.pdf` as one document per page; reject an empty corpus (`ingested_mock_data/seed_vector_ingest.py:23`).
3. Normalize source paths relative to the repository, reject empty pages, construct `<source>:page:<zero-based-index>` IDs (`ingested_mock_data/seed_vector_ingest.py:33`).
4. Create a loopback Chroma HTTP client and call its heartbeat (`ingested_mock_data/seed_vector_ingest.py:43`).
5. Create OpenAI embeddings with automatic long-input splitting disabled, then upsert pages into `parking_documents` (`ingested_mock_data/seed_vector_ingest.py:47`).
6. Fetch supplied IDs and verify the returned count before printing completion (`ingested_mock_data/seed_vector_ingest.py:54`).

### SQLite Fixture Flow

1. Fix random seed and snapshot time; construct 48 physical spot definitions across four facilities (`ingested_mock_data/seed_database.py:13`).
2. Construct 720 scheduled reservations for November 1–10 with snapshot-derived status (`ingested_mock_data/seed_database.py:35`).
3. Construct 1,440 daily spot records for November 1–30 with snapshot availability flags (`ingested_mock_data/seed_database.py:60`).
4. Enable foreign keys, create tables/index, and insert missing rows inside a transaction; print counts and close the connection in `finally` (`ingested_mock_data/seed_database.py:69`).

### PDF Rendering Flow

1. Resolve output folder and define facility/policy page content (`ingested_mock_data/generate_pdfs.py:12`).
2. Build each document using headings, paragraphs, explicit page breaks, metadata and footer callbacks (`ingested_mock_data/generate_pdfs.py:203`).
3. Write the twelve named PDF files; generation overwrites those outputs (`ingested_mock_data/generate_pdfs.py:212`, `ingested_mock_data/README.md`).

**State Management:**
- Working collections and clients are module-level variables in each script; there is no session or conversational state in `src/`.
- SQLite persistence preserves existing conflicting records on repeat runs (`ingested_mock_data/seed_database.py`).
- Chroma uses stable source/page IDs for upserts; deleted source PDFs do not cause deletion of existing vector records (`ingested_mock_data/seed_vector_ingest.py`, `ingested_mock_data/README.md`).

## Key Abstractions

**Daily transport slot:**
- Purpose: Represent one physical spot on one date, with type, price, hours and snapshot availability.
- Examples: `transport_slots` schema in `ingested_mock_data/seed_database.py`.
- Pattern: Composite primary key `(spot_id, slot_date)`; reference both fields from reservations.

**Reservation:**
- Purpose: Represent a fictional scheduled visit and customer/vehicle details.
- Examples: `reservations` schema in `ingested_mock_data/seed_database.py`.
- Pattern: Text identifier, constrained same-day start/end, status enum, foreign key to daily slot, index on spot/start/end.

**Reference page:**
- Purpose: Preserve one entire PDF page as a retrievable document.
- Examples: `documents` and `ids` in `ingested_mock_data/seed_vector_ingest.py`.
- Pattern: LangChain document with text, source metadata, zero-based page number and stable source/page identity.

## Entry Points

**Manual scripts:**
- Locations: `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, `ingested_mock_data/seed_vector_ingest.py`.
- Triggers: Direct Python execution; imports also execute their module-level work.
- Responsibilities: Seed SQLite, generate PDFs and ingest vectors, respectively.

**Infrastructure:**
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

**What happens:** Importing `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, or `ingested_mock_data/seed_vector_ingest.py` triggers writes or external-service work.
**Why it's wrong:** Reuse or test discovery can inadvertently mutate data or invoke paid embedding calls.
**Do this instead:** Treat them as explicit CLI scripts per `ingested_mock_data/README.md`; introduce callable functions and a `__main__` guard before importing their logic from application code.

### Duplicating domain definitions across fixture producers

**What happens:** Facility identifiers, prices, spot categories and hours appear independently in `ingested_mock_data/seed_database.py` and `ingested_mock_data/generate_pdfs.py`.
**Why it's wrong:** Structured facts and retrieval text can disagree when only one producer changes.
**Do this instead:** Review both producers together when editing domain facts; a shared fixture definition would require an explicit refactor, because none exists in `src/`.

## Error Handling

**Strategy:** Fail fast for ingestion prerequisites; otherwise propagate library exceptions. SQLite uses transaction scope and guaranteed close.

**Patterns:**
- `SystemExit` explains missing/mock key, no documents or blank pages in `ingested_mock_data/seed_vector_ingest.py`.
- `RuntimeError` signals failed post-ingest ID-count verification in `ingested_mock_data/seed_vector_ingest.py`.
- Database transaction handling and `finally: connection.close()` protect connection lifecycle in `ingested_mock_data/seed_database.py`.
- PDF generation has no explicit exception recovery in `ingested_mock_data/generate_pdfs.py`.

## Cross-Cutting Concerns

**Logging:** Plain `print()` completion/count/path output in the three `ingested_mock_data/*.py` scripts; no application logging framework is configured.
**Validation:** SQLite `CHECK`/foreign-key constraints and PDF page/key validation reside in `ingested_mock_data/seed_database.py` and `ingested_mock_data/seed_vector_ingest.py`.
**Authentication:** OpenAI uses environment configuration in `ingested_mock_data/seed_vector_ingest.py`; `docker/compose.yaml` binds Chroma to loopback. User authentication is not implemented in `src/`.

---

*Architecture analysis: 2026-11-09*

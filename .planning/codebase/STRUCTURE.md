# Codebase Structure

**Analysis Date:** 2026-11-09

## Directory Layout

```text
parking_reservation/
├── src/                          # Empty application source directory
├── ingested_mock_data/
│   ├── seed_database.py           # SQLite schema and deterministic fictional seed
│   ├── generate_pdfs.py           # ReportLab corpus content and rendering
│   ├── seed_vector_ingest.py      # PDF page loading, embedding and Chroma upsert
│   ├── parking_november_2026.sqlite3 # Existing fixture database
│   ├── pdfs/                     # Twelve generated facility/policy PDFs
│   └── README.md                 # Fixture semantics and execution instructions
├── docker/
│   └── compose.yaml              # Chroma container and named storage volume
├── .planning/                    # Planning and generated codebase reference material
├── .codex/                       # GSD agents, skills and workflow runtime
├── .venv/                        # Local Python environment
├── .env                          # Local environment configuration; contents not inspected
├── .gitignore                    # Python, environment and local configuration exclusions
├── .python-version               # Local interpreter selection
├── pyproject.toml                # Project metadata and runtime dependencies
├── uv.lock                       # Local dependency resolution lockfile
└── README.md                     # Empty root readme
```

## Directory Purposes

**`src/`:**
- Purpose: Application source location, currently empty.
- Contains: No implementation files, packages, routes or entry points detected.
- Key files: Not applicable; do not infer a LangGraph agent or backend from dependencies in `pyproject.toml`.

**`ingested_mock_data/`:**
- Purpose: Self-contained fictional fixture preparation.
- Contains: Three standalone Python scripts, a SQLite artifact, PDF corpus and usage documentation.
- Key files: `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, `ingested_mock_data/seed_vector_ingest.py`, `ingested_mock_data/README.md`.

**`ingested_mock_data/pdfs/`:**
- Purpose: Static reference documents consumed by the vector ingestion script.
- Contains: Facility guides `facility_ctr.pdf`, `facility_riv.pdf`, `facility_sta.pdf`, `facility_air.pdf`; policy PDFs for bookings, cancellations, payments, accessibility, charging, safety, terms and vehicle sizes.
- Key files: `ingested_mock_data/pdfs/booking_policy.pdf`, `ingested_mock_data/pdfs/pricing_and_payments.pdf`, `ingested_mock_data/pdfs/terms_of_service.pdf`.
- Author content in `ingested_mock_data/generate_pdfs.py`; PDF files are outputs rather than source text.

**`docker/`:**
- Purpose: Local supporting infrastructure definition.
- Contains: One Chroma Compose service, loopback port mapping and persistent named volume.
- Key files: `docker/compose.yaml`.

**`.codex/`:**
- Purpose: Repository-local agent workflow tooling.
- Contains: GSD skill and agent definitions plus GSD runtime implementation.
- Key files: `.codex/agents/gsd-codebase-mapper.toml`, `.codex/gsd-core/references/agent-skills-bootstrap.md`.
- Treat this tooling as separate from the parking application. Runtime tests or TypeScript files here are not application architecture evidence.

## Key File Locations

**Entry Points:**
- `ingested_mock_data/seed_database.py`: Directly executable standard-library SQLite seed.
- `ingested_mock_data/generate_pdfs.py`: Directly executable PDF rendering script requiring ReportLab.
- `ingested_mock_data/seed_vector_ingest.py`: Directly executable ingestion script using configured OpenAI credentials and running Chroma.
- `docker/compose.yaml`: Docker Compose entry point for Chroma infrastructure.

**Configuration:**
- `pyproject.toml`: Python requirement and dependencies; no CLI entry-point table or application build configuration is declared.
- `.python-version`: Interpreter version selector.
- `.gitignore`: Ignores `.venv/`, Python build/cache files, `uv.lock` and local environment configuration.
- `.env`: Present as local environment configuration; values are intentionally not inspected.
- `docker/compose.yaml`: Container image, network exposure and volume mapping.

**Core Logic:**
- `ingested_mock_data/seed_database.py`: Schema constraints, spot generation, schedule/status calculation and insert conflict behavior.
- `ingested_mock_data/generate_pdfs.py`: Fictional domain prose and facility definitions, layout styles and footer function.
- `ingested_mock_data/seed_vector_ingest.py`: PDF loading, page identity, embedding client and vector persistence.

**Testing:**
- No application test directory or test files are detected alongside `src/` or `ingested_mock_data/`; no testing configuration is declared in `pyproject.toml`.
- `.codex/gsd-core/` contains workflow tooling; do not report its checks as coverage of application scripts.

## Naming Conventions

**Files:**
- Use snake_case Python script names matching `ingested_mock_data/seed_database.py` and `ingested_mock_data/seed_vector_ingest.py`.
- Facility document outputs use lowercase code suffixes, such as `ingested_mock_data/pdfs/facility_ctr.pdf`.
- Policy document outputs use snake_case topic names, such as `ingested_mock_data/pdfs/cancellation_and_refunds.pdf`.
- The SQLite artifact explicitly names its fixture month: `ingested_mock_data/parking_november_2026.sqlite3`.

**Directories:**
- Use lowercase names and underscores where needed, matching `ingested_mock_data/`.
- `src/` has no existing domain/module subdivision to copy; choose application package boundaries explicitly when implementing application code.

## Where to Add New Code

**New Feature:**
- Primary application code: `src/`, which is currently empty. Establish an importable package and entry point explicitly; do not place live reservation behavior inside fixture seed scripts.
- Fixture-only changes: `ingested_mock_data/seed_database.py` for structured records, `ingested_mock_data/generate_pdfs.py` for reference corpus content, `ingested_mock_data/seed_vector_ingest.py` for ingestion behavior.
- Tests: No existing location is established. A new root `tests/` directory would be a new convention, not a currently implemented test suite; configure it through `pyproject.toml` when needed.

**New Component/Module:**
- Application implementation: Add under an explicit package in `src/`; no existing services, repositories, models or routers require alignment.
- Local infrastructure: Extend `docker/compose.yaml` for related supporting services.
- New corpus document: Add its content definition in `ingested_mock_data/generate_pdfs.py` and generated output under `ingested_mock_data/pdfs/`; the ingestion glob discovers PDFs recursively.
- Operational instructions: Update `ingested_mock_data/README.md` for fixture workflows; root `README.md` has no existing content structure.

**Utilities:**
- Shared application helpers: No existing shared utility module is detected in `src/`.
- Before extracting reusable logic from `ingested_mock_data/*.py`, add callable boundaries and main guards; the existing modules execute work on import.
- Keep facility identifiers/prices consistent between `ingested_mock_data/seed_database.py` and `ingested_mock_data/generate_pdfs.py` because no shared domain configuration exists.

## Special Directories

**`ingested_mock_data/pdfs/`:**
- Purpose: Generated reference corpus read by ingestion.
- Generated: Yes, by `ingested_mock_data/generate_pdfs.py`.
- Committed: No tracked files are detected in the current repository index; outputs are present as untracked workspace files.

**`.venv/`:**
- Purpose: Local installed Python environment.
- Generated: Yes.
- Committed: No; ignored in `.gitignore`.

**`.planning/codebase/`:**
- Purpose: Generated architecture and implementation reference documents.
- Generated: Yes, by codebase mapping.
- Committed: No tracked files are detected in the current repository index.

**`.codex/`:**
- Purpose: Agent/workflow runtime and skill definitions, separate from application source.
- Generated: Installed tooling; not generated by the parking fixture scripts.
- Committed: No; the current workspace reports `.codex/` as untracked.

---

*Structure analysis: 2026-11-09*

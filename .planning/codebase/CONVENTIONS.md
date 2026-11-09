# Coding Conventions

**Analysis Date:** 2026-11-09

## Naming Patterns

**Files:**
- Use descriptive snake_case Python script names, as in `ingested_mock_data/seed_database.py`, `ingested_mock_data/seed_vector_ingest.py`, and `ingested_mock_data/generate_pdfs.py`.
- PDF filenames use lowercase topic names and facility prefixes, such as `ingested_mock_data/pdfs/booking_policy.pdf` and `ingested_mock_data/pdfs/facility_ctr.pdf`.

**Functions:**
- Use snake_case for project functions: `page_footer(canvas, document)` in `ingested_mock_data/generate_pdfs.py` is the only explicit function definition in the application scripts.
- Most work executes as module-level statements and loops in all three scripts; there is no established service-method or application-handler convention under the empty `src/` directory.

**Variables:**
- Use snake_case names such as `local_timezone`, `occupied_now`, `daily_slots`, and `vector_store` in `ingested_mock_data/seed_database.py` and `ingested_mock_data/seed_vector_ingest.py`.
- Configuration-like values also use lowercase module-level variables (`snapshot`, `facilities`, `root`); uppercase Python constants are not an established convention in these scripts.
- Preserve cross-artifact facility codes (`CTR`, `RIV`, `STA`, `AIR`), spot IDs, and reservation IDs defined in `ingested_mock_data/seed_database.py` and described in `ingested_mock_data/README.md`.

**Types:**
- No project classes or type annotations are present in `ingested_mock_data/*.py`; data uses lists, tuples, sets, dictionaries, and library objects.
- SQLite column names are snake_case, with constrained string status/type values in `ingested_mock_data/seed_database.py`. Preserve these persisted names when extending consumers.

## Code Style

**Formatting:**
- No formatter configuration or formatter dependency is declared in `pyproject.toml`.
- Match four-space indentation, double-quoted strings, f-strings, parenthesized multiline calls, and blank lines between logical sections in `ingested_mock_data/seed_database.py`.
- Long prose strings and compact tuple rows are common in `ingested_mock_data/generate_pdfs.py`; no enforced line-length limit is detected.
- Keep SQL in triple-quoted strings and bind row values through `?` placeholders, following `ingested_mock_data/seed_database.py`.

**Linting:**
- No application Ruff, Flake8, Pylint, mypy, pre-commit, or equivalent configuration is detected; `pyproject.toml` contains project metadata and runtime dependencies only.
- No lint command or enforced lint rules are supplied by `pyproject.toml` or `ingested_mock_data/README.md`.

## Import Organization

**Order:**
1. Standard-library imports first (`os`, `pathlib`; `random`, `sqlite3`, `datetime`) in `ingested_mock_data/seed_vector_ingest.py` and `ingested_mock_data/seed_database.py`.
2. A blank line separates third-party imports such as `chromadb`, `dotenv`, and LangChain integrations in `ingested_mock_data/seed_vector_ingest.py`.
3. No application-local imports are present in `ingested_mock_data/*.py`; the scripts are independent entry points.

**Path Aliases:**
- Not detected. Use `Path(__file__)` to locate sibling outputs and the repository root, following all three scripts in `ingested_mock_data/`.
- Normalize PDF source metadata to repository-relative POSIX paths in `ingested_mock_data/seed_vector_ingest.py`; those paths form persisted vector-store identifiers.

## Error Handling

**Patterns:**
- Fail early with `SystemExit` for missing/mock API configuration, missing PDF pages, or blank page text in `ingested_mock_data/seed_vector_ingest.py`.
- Use an explicit exception for a failed postcondition: `ingested_mock_data/seed_vector_ingest.py` raises `RuntimeError` if Chroma returns fewer stored IDs than expected.
- Third-party loader, network, and embedding failures propagate directly in `ingested_mock_data/seed_vector_ingest.py`; no retries, wrapping, or centralized exception handler is present.
- Preserve the connection transaction context and `finally: connection.close()` in `ingested_mock_data/seed_database.py`; SQL failures propagate while connection cleanup is guaranteed.
- Keep SQLite integrity constraints with the schema in `ingested_mock_data/seed_database.py`: foreign keys, allowed statuses/types, date bounds, and timestamp ordering are enforced at persistence time.
- `ingested_mock_data/generate_pdfs.py` lets filesystem and ReportLab failures propagate without a recovery layer.

## Logging

**Framework:** Built-in `print`, as used in all three scripts under `ingested_mock_data/`.

**Patterns:**
- Print the database path and table counts after the transaction in `ingested_mock_data/seed_database.py`.
- Print ingestion count, target collection, and embedding model after verifying returned IDs in `ingested_mock_data/seed_vector_ingest.py`.
- Print each generated output path after building the PDF in `ingested_mock_data/generate_pdfs.py`.
- No structured logger, severity levels, or log configuration is established in `pyproject.toml` or `ingested_mock_data/*.py`.

## Comments

**When to Comment:**
- Start scripts with a module docstring describing purpose and execution requirements, as in `ingested_mock_data/seed_database.py` and `ingested_mock_data/seed_vector_ingest.py`.
- Explain domain caveats and persistence choices: snapshot availability is distinct from interval availability in `ingested_mock_data/seed_database.py`; stable page IDs and disabled input splitting are explained in `ingested_mock_data/seed_vector_ingest.py`.
- Keep operator setup instructions and dataset boundaries in `ingested_mock_data/README.md`.

**JSDoc/TSDoc:**
- Not applicable to the Python source in `ingested_mock_data/`. Python function docstrings are not used by `page_footer` in `ingested_mock_data/generate_pdfs.py`.

## Function Design

**Size:** No function-size rule is configured in `pyproject.toml`. `ingested_mock_data/generate_pdfs.py` has a short rendering callback; database generation and ingestion remain top-level procedural workflows.

**Parameters:** `page_footer(canvas, document)` in `ingested_mock_data/generate_pdfs.py` follows ReportLab's callback interface. Library constructors use keyword arguments for significant options, as in `Chroma(...)` and `OpenAIEmbeddings(...)` in `ingested_mock_data/seed_vector_ingest.py`.

**Return Values:** `page_footer` mutates the supplied canvas and returns implicitly. The three scripts produce filesystem/database/vector-store side effects and console summaries rather than application return objects (`ingested_mock_data/*.py`).

## Module Design

**Exports:** No explicit public export surface or package initializer is present under `ingested_mock_data/`. Each script performs work at import time, without a `__main__` guard. Do not import these modules merely to inspect constants or discover tests: `seed_database.py` writes SQLite, `generate_pdfs.py` writes PDFs, and `seed_vector_ingest.py` contacts external services after its configuration checks.

**Barrel Files:** Not applicable; there are no application re-export modules in `src/` or `ingested_mock_data/`.

---

*Convention analysis: 2026-11-09*

# Testing Patterns

**Analysis Date:** 2026-11-09

## Test Framework

**Runner:**
- No application test runner is detected. `pyproject.toml` declares runtime dependencies only, without test dependency groups or test configuration.
- No pytest, unittest suite, tox, nox, browser-test configuration, or application CI test workflow is present outside tooling/vendor directories. The application files are the three scripts in `ingested_mock_data/`; `src/` is empty.
- Exclude installed tooling and dependency tests under `.codex/` and `.venv/` from claims about application coverage.

**Assertion Library:**
- Not detected in `pyproject.toml` or `ingested_mock_data/*.py`. Explicit runtime guards and SQLite constraints are present, but they are not an automated test suite.

**Run Commands:**
- No run-all, watch, or coverage command is configured in `pyproject.toml` or documented in `ingested_mock_data/README.md`.
- Commands in `ingested_mock_data/README.md` seed SQLite, regenerate PDFs, or ingest embeddings. They mutate outputs and are not test commands.
- This mapping is based on source inspection; no seed script or external integration was executed.

## Test File Organization

**Location:**
- No application test directory or colocated test files are detected under `src/` or `ingested_mock_data/`.
- `ingested_mock_data/` holds demonstration data and generators, not a test harness.

**Naming:**
- No application test filename convention is established by `pyproject.toml` or the files under `ingested_mock_data/`.

**Structure:**
```text
ingested_mock_data/
  seed_database.py           # Data generator; writes SQLite
  generate_pdfs.py           # Corpus generator; writes PDFs
  seed_vector_ingest.py      # Live integration seed; embeds and stores pages
  parking_november_2026.sqlite3
  pdfs/                     # 12 reference PDFs
  README.md                 # Dataset and operating instructions
src/                        # Empty; no application tests
```

## Test Structure

**Suite Organization:**
- Not detected in `ingested_mock_data/*.py`; there are no test cases, test classes, or test decorators to reproduce.

**Patterns:**
- No per-test setup, teardown, assertions, or fixture lifecycle exists in `ingested_mock_data/*.py`.
- `ingested_mock_data/seed_database.py` uses `with connection` and `finally` for operational transaction handling and cleanup, not test setup/teardown.
- `ingested_mock_data/seed_vector_ingest.py` contains this runtime postcondition after a live ingestion operation:

```python
stored = vector_store.get(ids=ids, include=[])
if len(stored["ids"]) != len(ids):
    raise RuntimeError("Chroma did not return every ingested page ID.")
```

- The check in `ingested_mock_data/seed_vector_ingest.py` verifies returned ID count; it does not evaluate retrieval relevance, vector quality, page content equality, or stale-document deletion.

## Mocking

**Framework:** Not detected in `pyproject.toml` or `ingested_mock_data/*.py`.

**Patterns:**
- No monkeypatching, fake clients, dependency injection, or HTTP interception appears in `ingested_mock_data/seed_vector_ingest.py`; it constructs real Chroma and OpenAI clients.

**What to Mock:**
- No repository policy is established. The external boundaries are `chromadb.HttpClient`, `OpenAIEmbeddings`, PDF loading, and vector writes in `ingested_mock_data/seed_vector_ingest.py`; these require isolation before that workflow can be tested without live services.

**What NOT to Mock:**
- No repository policy is established in `pyproject.toml` or `ingested_mock_data/README.md`. The local SQLite schema and deterministic generation logic in `ingested_mock_data/seed_database.py` are independent of external APIs, but the script currently writes directly to its sibling database.

## Fixtures and Factories

**Test Data:**
- `ingested_mock_data/seed_database.py` uses a fixed random seed and snapshot to construct fictional rows. This is demonstration data, not a reusable test fixture factory:

```python
random.seed(202611)
database = Path(__file__).with_name("parking_november_2026.sqlite3")
local_timezone = timezone(timedelta(hours=1))
snapshot = datetime(2026, 11, 9, 12, tzinfo=local_timezone)
```

- `ingested_mock_data/README.md` documents 48 physical spots across 30 dates (1,440 daily rows), 720 reservations spanning November 1-10, and a fixed November 9 snapshot. These are documented expectations, not automated assertions.
- `ingested_mock_data/generate_pdfs.py` defines four facility guides and eight policy documents as nested tuples and lists, with three explicit page sections per PDF. `ingested_mock_data/README.md` describes 36 page documents for ingestion.
- Existing rows are preserved with `ON CONFLICT ... DO NOTHING` in `ingested_mock_data/seed_database.py`; rerunning does not reset a changed database to a fresh fixture.

**Location:**
- SQLite artifact: `ingested_mock_data/parking_november_2026.sqlite3`.
- Reference corpus: `ingested_mock_data/pdfs/`; generator: `ingested_mock_data/generate_pdfs.py`.
- Scope and expected counts: `ingested_mock_data/README.md`.

## Coverage

**Requirements:** None enforced in `pyproject.toml`; no application coverage configuration, threshold, or report is detected.

**View Coverage:** No command is supplied by `pyproject.toml` or `ingested_mock_data/README.md`.

## Test Types

**Unit Tests:**
- Not detected for the generation logic, date/status rules, stable ID construction, or PDF formatting in `ingested_mock_data/*.py`.

**Integration Tests:**
- No automated integration suite is detected. `ingested_mock_data/seed_vector_ingest.py` is an operational ingestion script with heartbeat and stored-ID checks, not an isolated integration test.
- SQLite foreign-key and check constraints in `ingested_mock_data/seed_database.py` provide runtime data validation but no regression assertions over the complete dataset.

**E2E Tests:**
- Not detected. `src/` has no application implementation; no browser/server end-to-end flow or test configuration is present in `pyproject.toml`.

## Common Patterns

**Async Testing:**
- Not applicable to the current synchronous scripts in `ingested_mock_data/`; no asynchronous tests or event-loop fixtures are detected.

**Error Testing:**
- No negative-path tests are detected. `ingested_mock_data/seed_vector_ingest.py` explicitly rejects absent/mock API configuration, an empty corpus, blank page text, and a stored-ID count mismatch.
- `ingested_mock_data/seed_database.py` constrains date ranges, allowed spot types/statuses, positive prices, boolean availability, timestamp ordering, and reservation-to-slot relationships; tests exercising rejected inserts are not present.
- Importing scripts to test these paths is unsafe for isolation: all three `ingested_mock_data/*.py` files execute their workflows at module scope. No temporary-output-path or injectable-client interface is provided.

---

*Testing analysis: 2026-11-09*

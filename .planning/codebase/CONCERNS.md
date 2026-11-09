# Codebase Concerns

**Analysis Date:** 2026-11-09

Scope: application assets in `ingested_mock_data/`, `docker/compose.yaml`, `pyproject.toml`, `.gitignore`, and the empty `src/` directory. Bundled agent/runtime tooling is excluded from application findings. Findings below distinguish verified implementation limits from conditional risks. No seed scripts or external services were executed.

## Tech Debt

**Dependency reproducibility and PDF generation setup:**
- Issue: `pyproject.toml` declares mostly lower-bound dependency constraints; `.gitignore` excludes `uv.lock`. A local lockfile exists but is not tracked. The PDF generator imports `reportlab`, which is not declared in the project dependencies.
- Files: `pyproject.toml`, `.gitignore`, `uv.lock`, `ingested_mock_data/generate_pdfs.py`, `ingested_mock_data/README.md`.
- Impact: A fresh checkout cannot rely on the local lock to reproduce the environment. `uv sync` alone does not declare or guarantee PDF regeneration dependencies; the fixture README separately instructs users to install ReportLab.
- Fix approach: Track the application lockfile and declare a PDF-generation optional dependency or dependency group. Keep the Chroma client/server version alignment explicit when updating dependencies.

**Import-time execution of operational scripts:**
- Issue: The three Python scripts perform their complete workflows at module scope. Importing the database script writes SQLite, importing the PDF generator overwrites output PDFs, and importing ingestion can call external services.
- Files: `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, `ingested_mock_data/seed_vector_ingest.py`.
- Impact: Tests and other modules cannot safely import helpers or fixture definitions without triggering side effects. The database script also seeds Python's process-wide random generator.
- Fix approach: Extract pure data-building functions and place execution behind `main()` and an `if __name__ == "__main__"` guard. Pass output paths and service clients explicitly; use a local `random.Random` instance.

**Repeated facts across database and reference corpus:**
- Issue: Facility codes, rates, space numbering, hours, dates, and policies are embedded in multiple script structures and prose strings.
- Files: `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, `ingested_mock_data/README.md`.
- Impact: Editing one representation can leave SQL facts and retrieved document facts inconsistent. This is a maintenance risk, not an observed discrepancy in the supplied rates.
- Fix approach: Centralize structured fixture facts and add cross-artifact assertions for rates, spot types, inventory and effective dates. Keep authored policy prose separate from the shared structured configuration.

## Known Bugs

**No confirmed current fixture corruption:**
- Evidence: Read-only inspection of `ingested_mock_data/parking_november_2026.sqlite3` returns `PRAGMA integrity_check = ok`, zero foreign-key violations, 1,440 daily slots, 720 reservations and zero overlapping pairs of non-cancelled reservations on the same spot.
- Files: `ingested_mock_data/parking_november_2026.sqlite3`, `ingested_mock_data/seed_database.py`.
- Limits: These checks validate the supplied SQLite artifact only; they do not establish PDF rendering quality, embedding success or service behavior. The following sections describe observable limitations rather than claiming reproduced runtime failures.

## Security Considerations

**External disclosure when expanding the PDF corpus:**
- Risk: Every matching PDF page is sent to OpenAI for embedding and its text is stored in Chroma. Adding real customer documents would change the data-handling requirements.
- Files: `ingested_mock_data/seed_vector_ingest.py`, `ingested_mock_data/README.md`, `ingested_mock_data/pdfs/`.
- Current mitigation: The supplied corpus is explicitly fictional, the script rejects missing/mock API keys, and `.gitignore` excludes local `.env` configuration. No credential contents were inspected.
- Recommendations: Before admitting real documents, define allowed input data and retention requirements, restrict corpus inputs, and validate that sensitive data is not included. Keep these as prerequisites for extending the fixture workflow, not claims of current leakage.

**Local Chroma trust boundary:**
- Risk: Chroma uses unauthenticated plain HTTP in the provided configuration. Local processes can access the exposed service; changing the host binding to a network interface would widen that access.
- Files: `docker/compose.yaml`, `ingested_mock_data/seed_vector_ingest.py`.
- Current mitigation: Docker publishes only `127.0.0.1:8000`; the client also targets loopback. Persistence uses a named Docker volume.
- Recommendations: Preserve loopback access for the local fixture. Add authentication, transport security and access controls before making the service reachable outside the development machine. No public exposure is established by the current Compose configuration.

**Future reservation access:**
- Risk: The fixture schema contains names and vehicle plates, but no application authorization or identity layer exists to govern future access.
- Files: `ingested_mock_data/seed_database.py`, `src/`.
- Current mitigation: Records are fictional and no application API is implemented.
- Recommendations: Require ownership checks and restrict fields before introducing real reservation lookup or agent database tools. Do not expose unrestricted SQL or treat a reservation identifier as proof of identity.

## Performance Bottlenecks

**Full-corpus embedding on every ingestion:**
- Problem: Stable IDs prevent duplicate records, but all pages are loaded and embedded on every run regardless of whether content changed.
- Files: `ingested_mock_data/seed_vector_ingest.py`, `ingested_mock_data/README.md`.
- Cause: `loader.load()` materializes the corpus and `add_documents(documents=documents, ids=ids)` receives the complete set. There is no content-hash comparison or checkpoint.
- Improvement path: For a larger corpus, compare content hashes, batch input, and checkpoint completed work. The supplied 12 PDFs/36 pages are small; no measured runtime bottleneck is established for them.

## Fragile Areas

**Vector collection lifecycle and model identity:**
- Files: `ingested_mock_data/seed_vector_ingest.py`, `ingested_mock_data/README.md`.
- Why fragile: IDs encode source path and page index, not content version. Removing a PDF or shortening one does not delete obsolete pages; renaming creates new IDs while old IDs remain. The embedding model is intentionally unspecified and collection naming does not encode its identity. Verification checks returned ID count, not that stored content or embeddings match the current source.
- Safe modification: Keep the documented one-off-seed scope explicit. For synchronization, reconcile the source ID set within an owned collection, store content hashes and explicit embedding configuration, and use a new collection or complete rebuild when changing model identity. Avoid deleting unrelated collections.
- Test coverage: No application tests exercise repeated ingestion, removed pages, renamed files, partial failures or model compatibility.

**SQLite rerun semantics:**
- Files: `ingested_mock_data/seed_database.py`, `ingested_mock_data/README.md`.
- Why fragile: `CREATE TABLE IF NOT EXISTS` does not migrate schemas, while conflict handling preserves existing rows rather than refreshing them. Changes to generated values are therefore not applied to records with the same key; partially edited fixture databases can retain inconsistent state on rerun.
- Safe modification: Preserve the documented non-destructive seed contract. Validate schema/data expectations explicitly and add a separate, clearly scoped rebuild or migration workflow if fixture evolution is needed.
- Test coverage: The supplied artifact passes read-only integrity and overlap checks, but no automated repeat-run or schema-change tests are present.

**PDF page boundaries are retrieval boundaries:**
- Files: `ingested_mock_data/generate_pdfs.py`, `ingested_mock_data/seed_vector_ingest.py`.
- Why fragile: PDF rendering uses flowable layout with fixed text saying "Page ... of 3". Longer content can spill to additional pages. Ingestion treats each actual PDF page as one document, rejects empty text, and disables automatic embedding input splitting.
- Safe modification: Validate generated page count, extracted text and page input size when editing prose; render-check overflow. Keep the page-level retrieval contract explicit or intentionally replace it with tested chunking.
- Test coverage: No automated page-count, text-extraction or embedding-input-size checks are present.

## Scaling Limits

**Fixed historical fixture and constrained schema:**
- Current capacity: `ingested_mock_data/seed_database.py` defines 48 spots, 30 slot dates and 720 scheduled reservations. The data snapshot is November 9, 2026 at noon, UTC+01:00.
- Limit: Slot constraints allow only November 2026; reservation constraints allow only November 1-10. Status and availability do not advance with the clock. Date comparisons operate on text, and the generator's fixed UTC offset is specific to the supplied November period.
- Scaling path: Keep the fixture as a fixture. A live service needs date-range-independent schema, timezone-aware interval handling, transactional conflict checks and derived current state. The existing daily availability flag is explicitly insufficient for interval searches.

**Booking integrity is not enforced as a live allocation system:**
- Current capacity: `ingested_mock_data/seed_database.py` generates non-overlapping visits and enables SQLite foreign keys for its own connection.
- Limit: The schema does not prohibit overlapping reservations, require business-hour boundaries or enforce whole-hour durations. Foreign-key enforcement must also be enabled on every future writer connection.
- Scaling path: Add transactional allocation logic and domain validation before introducing booking writes; validate concurrent attempts against the same spot. This is a future-use limitation, not evidence of overlapping supplied records.

## Dependencies at Risk

**Implicit embedding-library defaults:**
- Risk: `ingested_mock_data/seed_vector_ingest.py` depends on the installed OpenAI integration's default embedding model. `pyproject.toml` permits newer integration versions and `.gitignore` excludes the lockfile from tracking.
- Impact: A different resolved environment may change default behavior, making collection/query compatibility harder to reproduce.
- Migration plan: Pin the intended embedding model explicitly, record it with the collection and use the same configuration for retrieval. Preserve a reproducible dependency lock. No package vulnerability or unsupported-version claim is established by this analysis.

## Missing Critical Features

**Executable reservation application:**
- Problem: `src/` is empty; the repository supplies fixture and vector-ingestion scripts rather than a running reservation service or conversational agent. The root `README.md` is empty.
- Blocks: No user-facing search, authenticated reservation lookup, allocation, changes, cancellation, payment, or retrieval/answering workflow is implemented. Policies in `ingested_mock_data/generate_pdfs.py` describe fictional service behavior; they are not executable features.

**Operational diagnosis and recovery:**
- Problem: `ingested_mock_data/seed_vector_ingest.py` checks service heartbeat and final ID presence but has no application-level resume state, corpus reconciliation or structured operational logs. `docker/compose.yaml` defines persistence but no backup/restore workflow.
- Blocks: Reliable recovery and diagnosis for sustained ingestion or production storage are not provided. These are beyond the documented one-off seed scope in `ingested_mock_data/README.md`.

## Test Coverage Gaps

**Database and policy invariants:**
- What's not tested: Seed repeatability, preserved records, schema drift, status/availability at snapshot boundaries, adjacency versus overlap, policy-rate consistency and corruption handling.
- Files: `ingested_mock_data/seed_database.py`, `ingested_mock_data/generate_pdfs.py`, `pyproject.toml`.
- Risk: Fixture changes can silently alter the expected retrieval and availability answers. No application test files or test-runner configuration are detected.
- Priority: High when evolving fixtures or adding query logic.

**Ingestion contracts and failure handling:**
- What's not tested: Missing/mock configuration, empty corpus, blank PDF pages, stable IDs across working directories, service failure, stale-page removal behavior and whole-page input limits.
- Files: `ingested_mock_data/seed_vector_ingest.py`, `ingested_mock_data/README.md`.
- Risk: A change can leave a partial or stale collection while existence-only verification provides limited assurance. Use fake clients and fixture documents for ordinary tests; keep paid/network integration tests explicitly opt-in.
- Priority: High before reusing ingestion outside the supplied one-off workflow.

**PDF artifact and retrieval quality:**
- What's not tested: Expected 12-document/36-page corpus shape, extractable text, visual overflow, source citations and answer grounding.
- Files: `ingested_mock_data/generate_pdfs.py`, `ingested_mock_data/pdfs/`, `ingested_mock_data/seed_vector_ingest.py`.
- Risk: Rendering or content changes can degrade page-level retrieval without a Python exception. Retrieval-quality evaluation also requires a retrieval implementation, which is absent from `src/`.
- Priority: Medium for static fixture edits; high when implementing retrieval.

---

*Concerns audit: 2026-11-09*

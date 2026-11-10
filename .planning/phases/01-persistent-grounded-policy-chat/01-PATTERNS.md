# Phase 01: Persistent Grounded Policy Chat - Pattern Map

**Mapped:** 2026-11-10
**Files classified:** 29 proposed files, plus test-case/package-support groups
**Tracked analogs found:** 0 / 29

## File Classification

Names follow the research proposal; unspecified web/support names below are planner choices, not existing files.
Every closest tracked analog is **none**: `src/` is empty and the application inputs are currently untracked.

| New/modified file | Role | Data flow | Closest tracked analog |
|---|---|---|---|
| `src/parking/graph/state.py` | model | transform | none |
| `src/parking/graph/reducers.py` | utility | transform | none |
| `src/parking/graph/schemas.py` | model | request-response | none |
| `src/parking/graph/nodes.py` | service | request-response | none |
| `src/parking/graph/graph.py` | config | event-driven | none |
| `src/parking/checkpoint.py` | provider | file-I/O | none |
| `src/parking/retrieval.py` | service | request-response | none |
| `src/parking/settings.py` | config | file-I/O | none |
| `src/parking/api/app.py` | controller | request-response | none |
| `src/parking/api/sessions.py` | service | CRUD | none |
| `src/parking/api/submissions.py` | store | CRUD | none |
| `src/parking/api/gateway.py` | service | request-response | none |
| `src/parking/web/index.html` (inferred) | component | event-driven | none |
| `src/parking/web/app.js` (inferred) | component | event-driven | none |
| `src/parking/web/styles.css` (inferred) | component | transform | none |
| `langgraph.json` (inferred deployment JSON) | config | file-I/O | none |
| `docker/compose.yaml` | config | event-driven | none |
| `pyproject.toml` | config | file-I/O | none |
| `tests/conftest.py` (inferred) | test | file-I/O | none |
| `tests/unit/test_state.py` | test | transform | none |
| `tests/unit/test_policy_flow.py` | test | request-response | none |
| `tests/unit/test_guards.py` | test | transform | none |
| `tests/integration/test_api_contract.py` | test | request-response | none |
| `tests/integration/test_checkpointer_conformance.py` | test | file-I/O | none |
| `tests/integration/test_deployed_chat.py` | test | request-response | none |
| `tests/integration/test_chroma_retrieval.py` | test | request-response | none |
| `tests/integration/test_recovery.py` | test | event-driven | none |
| `tests/live/test_policy_cases.py` | test | request-response | none |
| `README.md` (inferred setup/smoke instructions) | config/documentation | file-I/O | none |

Also plan reviewed data under `tests/cases/` (test, transform), package markers if needed (config, file-I/O),
and a tested lock/environment policy. Exact case filenames and lock tracking are planner decisions.
No booking migrations, SQL availability services, administration screens, or corpus regeneration belong here.

## Pattern Assignments

No tracked implementation passes the analog gate. Do not label the seed scripts as runtime analogs.
For all files above, use `01-RESEARCH.md` implementation proposals and the newer locked context decisions.
The following excerpts are **untracked input compatibility references only**, not tracked analog assignments.
`git ls-files -- src ingested_mock_data pyproject.toml docker/compose.yaml` returned no paths.
These inputs are ordinary application assets, not ignored tooling mirrors; this report does not stage them.

### Retrieval/settings: preserve existing corpus integration

Untracked input `ingested_mock_data/seed_vector_ingest.py`, lines 10-14:

```python
import chromadb
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_openai import OpenAIEmbeddings
```

Use the Chroma/embedding imports in a new side-effect-free module; runtime retrieval needs no PDF loader.
Lines 35-42 establish source/page identity:

```python
    source = Path(document.metadata["source"]).relative_to(root).as_posix()
    page = document.metadata["page"]  # PyPDFLoader page indices are zero-based.
    if not document.page_content.strip():
        raise SystemExit(f"Empty text on page {page + 1} of {source}.")
    document.metadata["source"] = source
    # Stable IDs let Chroma upsert the same pages on a rerun instead of duplicating them.
    ids.append(f"{source}:page:{page}")
```

Lines 44-53 establish connection/collection compatibility:

```python
client = chromadb.HttpClient(host="127.0.0.1", port=8000, ssl=False)
client.heartbeat()
# Leave model unspecified to use langchain_openai's default embedding model.
# Disable automatic long-input splitting too: each full page is embedded as-is.
embeddings = OpenAIEmbeddings(check_embedding_ctx_length=False)
vector_store = Chroma(
    client=client,
    collection_name="parking_documents",
    embedding_function=embeddings,
)
```

Parameterize host/port for container DNS. Establish historical embedding compatibility before retrieval;
the unspecified model is not proof of collection provenance. Keep reads bounded and preserve IDs;
public citations use allowlisted titles and one-based pages. Never copy the following ingestion writes.

### Deployment: preserve existing Chroma storage

Untracked input `docker/compose.yaml`, lines 2-9:

```yaml
  chromadb:
    image: chromadb/chroma:1.5.9
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      CHROMA_PERSIST_PATH: /data
    volumes:
      - chroma_data:/data
```

Extend with real readiness checks and healthy dependencies; preserve the named volume.
Add PostgreSQL/Redis server infrastructure and a separate persistent checkpoint directory.
Build/start and verify the graph image before accepting SDK-backed API integration.

## Shared Patterns

- **Lifecycle:** Existing seed scripts execute on import. Read their source; never import them from application/tests.
- **Persistence:** D-09–D-12 override older PostgreSQL-checkpointer advice. Use exact `SqliteSaver` in a separate DB; create its connection outside graph execution in a local closure/lifecycle. No connection in runtime context/state. Verify the proposed async adapter, drain/close behavior, conformance and deployed restart before acceptance; no substitute saver.
- **State:** Stable request/query/message identities; immutable evidence merge retains prior questions and both retrieval attempts, with idempotent replay and conflict detection. One silent semantic rewrite; outages remain service failures.
- **Privacy/errors:** No existing auth/error-handler analog. Implement server-side session/thread/request ownership before SDK calls, validated DTOs and explicit CORS; final guard is the sole reply publisher. Never proxy raw graph streams/state or expose seed-style exceptions to customers.
- **Recovery/UI:** Durable submission registry reconciles accepted/unknown runs without blind recreation. Refresh recovers pending requests; duplicate tabs obtain separate threads; New chat detaches immediately. Preserve pending draft and disable Send. Browser session restoration remains an explicit D-06 verification limitation.
- **Validation/testing:** No existing Pydantic boundaries, pytest fixtures or automated tests. Introduce deterministic isolation, read-only real-corpus cases, saver conformance and deployed SDK/restart/recovery gates; skipped live checks remain unverified.

## No Analog Found

All 29 classified files lack tracked analogs. In particular there is no existing graph, reducer,
API, UI, session/ownership registry, SDK recovery layer, or checkpointer implementation.
The ingestion script's batch upsert is not a request-response retrieval implementation.

## Metadata

**Search scope:** `src/`, `tests/`, `ingested_mock_data/`, `docker/`, manifest and phase inputs.
**Application inventory:** five text files under fixture/deployment directories plus the manifest; no tests.
**Tracked-source check:** zero application paths returned; no tooling paths offered as analogs.
**Pattern extraction date:** 2026-11-10. Read-only analysis; only this artifact was written.

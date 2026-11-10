# Phase 1: Persistent Grounded Policy Chat - Context

**Gathered:** 2026-11-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a simple customer policy chat through a deployed LangGraph Agent Server and SDK-backed FastAPI. Answers use the existing Chroma policy corpus, structured evidence assessment, safe response boundaries, persistent thread memory, and retained per-query evidence. Build/start the graph image before integrating the API through `langgraph_sdk`.

The owning requirements are GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-06, RAG-02, RAG-05, RAG-07, PRIV-01, PRIV-05, API-01, API-05, DEL-02, and DEL-04. Prerequisite privacy, documentation, UI, and verification work accompanies this usable slice even when a later phase owns the complete requirement.

Live SQL availability/grid belongs to Phase 2; conversational booking writes belong to Phase 3; administrator decisions and cancellation belong to Phase 4. Phase 1 must not claim those later capabilities are operational. Existing choices remain locked: `gpt-6-luna`, LangChain/LangGraph only, a simple frontend, the local trusted no-login/no-application-key deployment, and preservation of existing assets.

</domain>

<decisions>
## Implementation Decisions

### Answers and Sources

- **D-01:** Match the customer's message language. English questions receive English answers; Polish questions receive Polish answers.
- **D-02:** Answer concisely by default: a direct answer in 2–4 sentences, using bullets when useful. This does not require omitting relevant caveats or compressing a four-facility comparison into an unreadable paragraph.
- **D-03:** Put source citations inline beside the supported claims. Retain document and page identity so citations can be checked; do not expose private filesystem paths or raw internal state.
- **D-04:** Use a friendly, straightforward tone: natural, polite, and practical.

### Conversation Continuity and Checkpoint Storage

- **D-05:** Refreshing the page restores its current messages and continues the same thread.
- **D-06:** Closing and reopening the browser starts a fresh conversation. Do not automatically reopen the previous thread across that browser-session boundary. Previously stored threads are not deleted by this behavior.
- **D-07:** Each tab has its own conversation/thread. Opening or duplicating a tab must not unintentionally share the originating tab's thread; refresh within a tab retains its own thread.
- **D-08:** New chat starts a fresh thread immediately, without confirmation, and leaves the previous thread stored. A history browser or automatic thread deletion was not requested.
- **D-09:** Use `SqliteSaver` for graph checkpoints in a separate SQLite database, distinct from `ingested_mock_data/parking_november_2026.sqlite3`. This is an explicit user implementation constraint and applies to application persistence, not merely tests.
- **D-10:** Create the checkpoint database connection outside the graph. Keep it in a local variable/closure accessible to graph construction/checkpointer wiring; do not pass the connection as runtime context or store a live connection in graph state. Manage its lifetime outside graph-node execution.
- **D-11:** D-09/D-10 supersede the earlier research recommendation to rely exclusively on the Agent Server's default PostgreSQL checkpointer. PostgreSQL/Redis may remain required server infrastructure; their existence does not satisfy the requested separate SQLite checkpoint persistence.
- **D-12:** Verify the pinned Agent Server's custom-checkpointer integration, async method requirements, and conformance against the exact requested `SqliteSaver` arrangement. The official custom-checkpointer guide describes an async lifecycle and required async operations, so this is a planning/setup compatibility gate. Do not silently substitute `AsyncSqliteSaver`, PostgreSQL checkpoints, or an in-process API graph; report any unresolved incompatibility explicitly.

### Unclear and Unsupported Questions

- **D-13:** If a facility-specific question names no facility and none is clear from context, briefly compare all four facilities (CTR, RIV, STA, AIR) instead of asking the customer to select one first. Compare only supported facts and keep the presentation concise.
- **D-14:** When evidence answers only part of a comparison or question, answer supported parts with citations and clearly mark the remaining information as unavailable. Missing evidence for one facility must not produce invented facts about it.
- **D-15:** If evidence is insufficient, have the LLM rewrite the retrieval query once to improve semantic matching while preserving the customer's original meaning. Retrieve again and reassess evidence. This is a bounded single retry, not an unbounded loop or permission to answer from general model knowledge.
- **D-16:** Keep the original customer message/query identity. Record any rewritten query, attempt, and retrieved evidence internally under the same question; preserve earlier question evidence. A search rewrite must not become a new customer message or erase the first retrieval attempt.
- **D-17:** If the second retrieval/assessment still cannot support an answer, state that the question is unsupported by the available information and ask the customer for a new question. Use the selected language and friendly, concise tone.
- **D-18:** The rewrite/retrieval retry is silent. Do not show rewritten queries, search status, evidence-judge details, or internal processing to the customer. Dependency failures remain explicit service errors rather than being disguised as insufficient evidence or triggering a semantic rewrite by themselves.

### Chat Interaction and Recovery

- **D-19:** Customers see only the final checked reply. Do not display internal steps or progress labels such as Checking, Searching documents, Checking the answer, or query-rewrite status. Do not stream unguarded partial responses or raw tool/graph events to the browser.
- **D-20:** While a request is pending, allow the customer to type a draft but disable Send. Preserve the draft while the current reply completes; do not silently submit or queue another turn.
- **D-21:** A temporary request failure produces a brief customer-safe error and a Retry button. Keep the original message and conversation intact; internal exceptions and infrastructure details stay outside the customer response.
- **D-22:** After page refresh or connection loss while a reply is pending, recover the existing request and display its result without resubmitting the question. Distinguish reconnecting to an accepted request from retrying a failed operation so recovery does not duplicate turns, query indices, or later booking effects.

### Agent Discretion and Planning Checks

- No additional product behavior was delegated through a "you decide" selection. Researchers/planners may choose small implementation details that satisfy these decisions and the approved requirements.
- Choose connection lifecycle, SQLite file location/configuration, local ownership storage, request identity, and frontend state mechanics during planning. Preserve the separate checkpoint/booking databases and the required outside-graph local connection.
- Verify browser close/reopen behavior, including restored tabs, without accidentally treating a copied tab identifier as authorization. Server-side ownership checks remain mandatory despite the absence of account login.
- Choose a backend same-thread concurrency policy compatible with disabled Send and safe retry/recovery. Frontend button state alone is not enforcement.
- Define reviewed policy questions, source/page expectations, unsupported cases, partial answers, and a case that succeeds only after the single rewrite. Test the deployed saver/SDK path, not only an in-memory test graph.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents must read these references before planning or implementing. Paths below are relative to the repository root. This context records newer user choices where earlier research differs.**

### Approved Scope and State

- `.planning/PROJECT.md` — project goals, existing assets, fixed technology choices, local trust boundary, and readability preference.
- `.planning/REQUIREMENTS.md` — approved v1 requirements, ownership, acceptance criteria, and scope exclusions.
- `.planning/ROADMAP.md` — Phase 1 boundary, prerequisite ordering, success criteria, and subsequent phases.
- `.planning/STATE.md` — current progress and session handoff.
- `.planning/config.json` — selected workflow settings; automatic workflow advancement is disabled.

### Research and Existing Integration Evidence

- `.planning/research/SUMMARY.md` — setup gates, vertical-slice rationale, and unverified runtime assumptions.
- `.planning/research/ARCHITECTURE.md` — graph/API boundaries, safe outputs, thread concurrency, and deployed integration; its default-PostgreSQL-checkpointer recommendation is superseded by D-09–D-12.
- `.planning/research/STACK.md` — candidate dependencies, requested model, embedding compatibility, and Agent Server prerequisites; verify pinned runtime behavior.
- `.planning/codebase/STACK.md` — existing Python and dependency baseline.
- `.planning/codebase/INTEGRATIONS.md` — current Chroma, embedding, storage, and environment integration points.
- `ingested_mock_data/README.md` — fictional corpus, finite November coverage, page-level ingestion, and operational commands.
- `ingested_mock_data/seed_vector_ingest.py` — source/page normalization, collection name, embedding setup, and stable IDs; importing executes ingestion.
- `docker/compose.yaml` — existing persistent local Chroma service to extend with readiness and application services.

### Framework Reference Checked During Discussion

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) — thread-scoped checkpoints and default server-managed persistence.
- [Custom Agent Server checkpointer](https://docs.langchain.com/langsmith/custom-checkpointer) — custom lifecycle, deployment configuration, async base capabilities, and conformance checks; verify against the pinned runtime before implementation.

No external user-provided specification or ADR was introduced during this discussion.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `parking_documents` contains the previously inspected 36 pages from 12 fictional PDFs, with source/page metadata. Preserve the existing collection while establishing embedding compatibility.
- `ingested_mock_data/pdfs/` supplies four facility guides and eight policy documents for citation and comparison cases.
- `ingested_mock_data/seed_vector_ingest.py` already uses `langchain_chroma.Chroma`, `OpenAIEmbeddings`, and page-level IDs. Reuse the integration concepts without importing its operational side effects.
- `docker/compose.yaml` already supplies Chroma storage. Extend the deployment rather than creating a conflicting independent collection/service.

### Established Patterns

- Python >=3.12 and uv are the existing development baseline. Scripts resolve repository/fixture paths from `__file__` and normalize persisted document paths to repository-relative POSIX form.
- Existing ingestion leaves the embedding model unspecified; vector dimensions do not establish model identity. Query embeddings must be compatible with the stored collection.
- `src/` has no implemented application graph, API, UI, or session layer to reuse. Prefer clear, small modules rather than introducing unnecessary framework abstractions.
- The booking SQLite fixture is operational domain data and must remain distinct from the new checkpoint database. The reported NumPy/Chroma import failure remains an environment setup check.

### Integration Points

- New graph construction/checkpointer setup, retrieval/judge/guard nodes, and typed state belong under the new application source.
- FastAPI uses `langgraph_sdk` against the deployed graph and exposes only safe response projections. Restore/reconnect behavior must preserve request and thread ownership.
- The simple customer frontend connects to this API for final replies, per-tab continuity, immediate New chat, pending-send control, and Retry.
- Persistent volumes/configuration must keep the SQLite checkpoint file available across graph-server restarts while leaving the booking database separate.

</code_context>

<specifics>
## Specific Ideas

- User instruction: "make sure the checkpointer is another separate sqllite db" and "SqliteSaver".
- User instruction: "implement the connection ouside of the graph and dont need to pass it as runtime context, it will be accessed via loc variable (the connection)".
- User requested an LLM semantic query reformulation before declaring a question unsupported; the confirmed interpretation is one silent, meaning-preserving retry.
- User instruction: "customer should not see what assistant is doing"; the confirmed behavior displays only the final guarded reply.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 1 scope. Live slot/grid behavior, booking creation, administrator decisions, and cancellation remain in their already approved later phases.

</deferred>

---
*Phase: 01-persistent-grounded-policy-chat*
*Context gathered: 2026-11-10; all four discussion areas and context creation confirmed by the user.*

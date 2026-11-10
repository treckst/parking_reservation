---
type: quick
status: complete
---

# Hybrid retrieval, tracing and container API/UI

1. Read the existing Chroma pages into a scoped BM25 retriever and combine with
   scoped dense retrieval using LangChain EnsembleRetriever weights 0.4/0.6.
   Preserve corpus, source/page IDs, facility scope and bounded outputs.
2. Make graph tracing/key/project settings environment interpolations. Package
   FastAPI and static UI in a dedicated image with persistent registry storage,
   container DNS and service_healthy dependency on graph.
3. Add focused hybrid tests and deployment documentation, build/start updated
   services and check HTTP UI/static/API readiness without paid model calls.
   Existing phase acceptance debt remains separate. Execute inline, no agents.

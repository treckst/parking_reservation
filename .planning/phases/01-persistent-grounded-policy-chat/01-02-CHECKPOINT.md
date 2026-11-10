---
phase: 01-persistent-grounded-policy-chat
plan: "02"
status: superseded-by-user-override
date: 2026-11-10
resume_task: 01-02-01
---

# Deployment prerequisite checkpoint

Superseded on 2026-11-10: the user explicitly requested execution with
`--yolo --skip-gates --no-verify`. Credential and acceptance gates no longer
pause this run. The absence of credentials is not converted into a successful
deployment claim; see 01-EXECUTION.md and the new plan summaries.

Restored the committed versions of src/parking/checkpoint.py,
src/parking/settings.py and tests/integration/test_checkpointer_conformance.py
with explicit user authorization. `uv run --locked pytest -q`: 28 passed in
10.43 seconds. No live provider calls were made.

Docker daemon reports 29.7.2. A temporary container using the existing local
langchain/langgraph-api:3.12 image reports langgraph-api 0.17.1. Its configuration
and _checkpointer module contain the custom lifecycle hook. This is source-level
compatibility evidence, not a deployed hook/conformance/restart pass.

Presence-only credential checks found an OPENAI_API_KEY entry in root .env, but
no LANGSMITH_API_KEY, LANGCHAIN_API_KEY or LANGGRAPH_CLOUD_LICENSE_KEY in either
the process environment or root .env. Secret values were not printed.

Task 01-02-01 explicitly requires required server credentials to be available.
The official standalone-server guide documents server authentication credentials:
https://docs.langchain.com/langsmith/deploy-standalone-server

Await a deployment credential configured locally or a user-authorized revision
of this prerequisite. Do not replace the deployment with an in-process graph,
substitute checkpoint storage, or claim successful deployed acceptance. No
Plan 01-02 production changes, build, running deployment or completed SUMMARY
were created. Resume task 01-02-01 after resolving this prerequisite; retain the
explicit override removing live OpenAI authentication/provenance preflights.

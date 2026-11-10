# Phase 1 prerequisite resolution

Status: Resolved by explicit user instruction on 2026-11-10.

Phase 1 does not require embedding provenance configuration or a live OpenAI authentication probe. No provider credentials are needed to run the automated tests.

The application uses LangChain directly:

```python
embeddings = OpenAIEmbeddings(check_embedding_ctx_length=False)
llm = ChatOpenAI(model="gpt-6-luna")
```

Unit tests mock the constructors and provider calls, remove the API key from the test environment, and block network connections. Run `uv run --locked pytest -q`.

The original failed live probes are historical evidence only. Do not rerun them or restore those requirements. Continue plan 01-01 at task 01-01-02, implementing and checking the separate SQLite SqliteSaver. The plan and phase are not yet complete.

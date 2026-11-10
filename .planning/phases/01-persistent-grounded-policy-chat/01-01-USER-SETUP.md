# Phase 1 runtime prerequisite checkpoint

Status: Incomplete. Plan 01-01 halted during task 01-01-01; task 01-01-02 and all dependent plans have not started.

## Provider access

Update `OPENAI_API_KEY` in the ignored root `.env` with a valid key that can access `gpt-6-luna`. Do not send the key in chat. An existing shell environment variable takes precedence over `.env`; update or remove that value if it holds the invalidated key. This credential belongs to the backend; customers and administrators do not need API keys.

The actual live probe returned HTTP 401, "Your API key has been invalidated." No alternate model was selected.

## Existing embedding model

Set `PARKING_EMBEDDING_MODEL` to the model that generated the stored `parking_documents` vectors. The ingestion script leaves this argument unspecified. Its README mentions `text-embedding-ada-002`, but that alone does not establish the historical collection's model.

Set `PARKING_EMBEDDING_PROVENANCE` to a local JSON file containing the model, collection, evidence, and reviewed query/source/page cases. For example, fill this structure with actual ingestion evidence and reviewed corpus cases:

```json
{
  "model": "<verified ingestion model>",
  "collection": "parking_documents",
  "evidence": "<ingestion log or independently reviewed vector comparison>",
  "reviewed_queries": [
    {
      "query": "<reviewed policy question>",
      "source": "ingested_mock_data/pdfs/<actual document>.pdf",
      "page": 0,
      "k": 4
    }
  ]
}
```

Pages are zero-based. The probe re-embeds one existing page, compares its vector with the stored vector, and tests the reviewed retrieval expectations. It only reads Chroma; it does not recreate or re-ingest the collection.

## Resume verification

```powershell
uv run --locked pytest tests/integration/test_runtime_prerequisites.py -m live_model --require-external -q
```

Both external cases must pass. Then resume `$gsd-execute-phase 1` at the halted plan; do not skip to deployment or treat the halted summary as completed work.

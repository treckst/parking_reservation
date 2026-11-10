# November 2026 mock data

Run `python ingested_mock_data/seed_database.py` from the repository root. It uses
only Python's standard library and creates `parking_november_2026.sqlite3` beside
the script. Paths are relative to the script, so running from another directory
also works. Existing records are preserved on repeat runs; this is a one-off
fixture, not a migration or live availability service.

- `transport_slots`: 48 physical spots x 30 dates = 1,440 rows, November 1-30.
  The composite key `(spot_id, slot_date)` identifies a daily spot record.
- `reservations`: 720 reservations with start/end dates November 1-10 inclusive.
  `spot_id` and `slot_date` link each reservation to its daily spot record.
  `created_at` may be in October because bookings can be made in advance.
- Fixed snapshot: November 9, 2026 at 12:00, Europe/Warsaw (UTC+01:00).
  Availability is 0 for past dates and spots occupied at the snapshot, otherwise 1.
  Check non-cancelled reservation overlaps as well when answering availability
  questions for a specific interval. Statuses are schedule-based, not entry logs.
- Prices are PLN/hour. Working hours are 06:00-22:00 daily. All people, plates,
  facilities and addresses are fictional. Prefixes CTR, RIV, STA and AIR match
  the facility guides. No real bookings or payments are represented.

`pdfs/` contains 12 text-based PDFs, each with three pages: four facility guides
and eight policy documents. They use single-column text, descriptive headings,
document metadata, page numbers and explicit scope. All policies are fictional,
version 1.0, effective November 1-30, 2026. These are static reference documents;
query SQLite for individual reservations and interval availability.

The PDFs are already generated. To regenerate, install `reportlab` in your Python
environment and run `python ingested_mock_data/generate_pdfs.py`. This overwrites
only the 12 named PDF outputs. PDF packages are not needed to seed SQLite.

## Load the PDFs into Chroma

The Docker Compose configuration is `docker/compose.yaml`. It uses the prebuilt
`chromadb/chroma:1.5.9` image, publishes `127.0.0.1:8000`, and persists Chroma data
in a named Docker volume mounted at `/data`. No image build is needed.

From the repository root, when ready:

```powershell
uv sync
docker compose -f docker/compose.yaml up -d
# Replace the mock OPENAI_API_KEY in the root .env, then run:
uv run python ingested_mock_data/seed_vector_ingest.py
```

The root `.env` is ignored by Git. An existing `OPENAI_API_KEY` environment variable
takes precedence over the `.env` value. The ingestion script refuses the supplied
mock key before contacting either service.

`seed_vector_ingest.py` uses the community `DirectoryLoader` with
`PyPDFLoader(mode="page")` and `langchain_chroma.Chroma` over HTTP. All 12 PDFs
produce 36 documents, one per page. There is no text splitting, overlap or further
chunking. Source paths and zero-based page numbers are retained in metadata.

`OpenAIEmbeddings` uses its default model (currently `text-embedding-ada-002`),
with automatic long-input splitting disabled. Each page is sent whole to OpenAI
for embedding; the resulting vectors and text are stored in `parking_documents`.
Future oversized pages will fail the embedding API's input limit rather than
being silently split. The supplied pages are short.

Stable source-and-page IDs make repeat runs update the same records rather than
add duplicates. Rerunning still makes embedding API calls. This is a one-off seed,
not a directory synchronizer: removing a PDF does not delete previously stored
pages. Reuse the same embedding model when querying this collection.

To stop Chroma while keeping its data:

```powershell
docker compose -f docker/compose.yaml down
```

Implementation references: [Chroma Docker setup](https://cookbook.chromadb.dev/running/running-chroma/),
[LangChain Chroma integration](https://docs.langchain.com/oss/python/integrations/vectorstores/chroma),
and [OpenAI embedding inputs](https://developers.openai.com/api/reference/resources/embeddings/methods/create).

"""One-off PDF ingestion: uv run python ingested_mock_data/seed_vector_ingest.py.

Start docker/compose.yaml and populate the root .env first.
Each PDF page is one vector-store document; no text splitter is used.
"""

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_openai import OpenAIEmbeddings


root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env")
api_key = os.getenv("OPENAI_API_KEY", "").strip()
if not api_key or api_key.startswith("sk-mock-"):
    raise SystemExit("Replace OPENAI_API_KEY in the root .env with your real key first.")

loader = DirectoryLoader(
    str(Path(__file__).with_name("pdfs")),
    glob="**/*.pdf",
    loader_cls=PyPDFLoader,
    loader_kwargs={"mode": "page"},
)
documents = loader.load()
if not documents:
    raise SystemExit("No PDF pages found in ingested_mock_data/pdfs/.")

ids = []
for document in documents:
    source = Path(document.metadata["source"]).relative_to(root).as_posix()
    page = document.metadata["page"]  # PyPDFLoader page indices are zero-based.
    if not document.page_content.strip():
        raise SystemExit(f"Empty text on page {page + 1} of {source}.")
    document.metadata["source"] = source
    # Stable IDs let Chroma upsert the same pages on a rerun instead of duplicating them.
    ids.append(f"{source}:page:{page}")

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
vector_store.add_documents(documents=documents, ids=ids)
stored = vector_store.get(ids=ids, include=[])
if len(stored["ids"]) != len(ids):
    raise RuntimeError("Chroma did not return every ingested page ID.")

print(f"Ingested {len(documents)} PDF pages into 'parking_documents' at http://127.0.0.1:8000.")
print(f"Embedding model: {embeddings.model}")

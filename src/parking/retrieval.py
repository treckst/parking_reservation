"""Read-only, bounded retrieval from the existing page collection."""

from functools import lru_cache
import re

import chromadb
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from parking.models import create_embeddings
from parking.settings import Settings
from parking.graph.schemas import EvidenceDocument


TITLES = {
    "accessible_parking": "Accessible parking",
    "booking_policy": "Booking policy",
    "cancellation_and_refunds": "Cancellation and refunds",
    "electric_vehicle_charging": "Electric vehicle charging",
    "entry_exit_and_safety": "Entry, exit and safety",
    "facility_air": "Airport Approach (AIR)",
    "facility_ctr": "Central Courtyard (CTR)",
    "facility_riv": "Riverside Yard (RIV)",
    "facility_sta": "Station East (STA)",
    "pricing_and_payments": "Pricing and payments",
    "terms_of_service": "Terms of service",
    "vehicle_size_rules": "Vehicle size rules",
}
SOURCES = {f"ingested_mock_data/pdfs/{name}.pdf": title for name, title in TITLES.items()}


@lru_cache(maxsize=1)
def vector_store():
    settings = Settings.from_env()
    client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    client.heartbeat()
    # create_collection_if_not_exists=False prevents accidental corpus creation.
    return Chroma(
        client=client, collection_name="parking_documents",
        embedding_function=create_embeddings(), create_collection_if_not_exists=False,
    )


def retrieve(question: str, facilities: list[str]) -> list[dict]:
    results = {}
    for facility in facilities:
        if facility not in {"CTR", "RIV", "STA", "AIR"}:
            raise ValueError("Unsupported facility")
        source = f"ingested_mock_data/pdfs/facility_{facility.lower()}.pdf"
        search_scope(results, question, (source,), 2)
    shared = tuple(source for source in SOURCES if "/facility_" not in source)
    search_scope(results, question, shared, 4)
    # Preserve reciprocal-rank fusion order within each bounded scope.
    return list(results.values())


def tokenize(text):
    """Unicode words retain Polish letters; punctuation/case do not split matches."""
    return re.findall(r"\w+", text.casefold())


def normalize_documents(documents, sources):
    results = {}
    for document in documents:
        if document.metadata.get("source") in sources:
            add_document(results, document)
    return [Document(
        id=record["id"], page_content=record["text"], metadata={
            "source": record["source"], "page": record["page"],
            "evidence_id": record["id"],
        },
    ) for record in results.values()]


def create_ensemble(store, sources, k):
    """Both retrievers use the same approved Chroma pages and source scope."""
    source_filter = {"source": {"$in": list(sources)}}
    corpus = store.get(where=source_filter, limit=37, include=["documents", "metadatas"])
    if len(corpus["ids"]) > 36:
        raise ValueError("Policy corpus exceeds the supported 36-page scope")
    documents = normalize_documents([
        Document(page_content=text, metadata=metadata)
        for text, metadata in zip(corpus["documents"], corpus["metadatas"], strict=True)
        if isinstance(text, str) and isinstance(metadata, dict)
    ], sources)
    if not documents:
        return None
    # Sorting gives keyword ties a repeatable corpus order.
    documents.sort(key=lambda doc: doc.metadata["evidence_id"])
    bm25_retriever = BM25Retriever.from_documents(documents, k=k, preprocess_func=tokenize)
    dense_retriever = store.as_retriever(search_kwargs={"k": k, "filter": source_filter}) | RunnableLambda(
        lambda docs: normalize_documents(docs, sources)
    )
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, dense_retriever],
        weights=[0.4, 0.6],
        id_key="evidence_id",
    )
    return ensemble_retriever


@lru_cache(maxsize=8)
def hybrid_retriever(sources, k):
    # The reference collection is static; restart graph after deliberate corpus changes.
    return create_ensemble(vector_store(), sources, k)


def search_scope(results, question, sources, k):
    retriever = hybrid_retriever(sources, k)
    if retriever is not None:
        for document in retriever.invoke(question)[:k]:
            add_document(results, document)


def add_document(results, document):
    source, page = document.metadata.get("source"), document.metadata.get("page")
    if source not in SOURCES or type(page) is not int or not 0 <= page <= 2:
        return
    if not document.page_content.strip():
        return
    record = EvidenceDocument(
        id=f"{source}:page:{page}", source=source, page=page, title=SOURCES[source],
        text=document.page_content[:16000],
    ).model_dump()
    if record["id"] in results and results[record["id"]] != record:
        raise ValueError("Conflicting corpus pages")
    results[record["id"]] = record

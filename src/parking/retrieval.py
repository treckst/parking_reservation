"""Read-only, bounded retrieval from the existing page collection."""

from functools import lru_cache

import chromadb
from langchain_chroma import Chroma

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
    store = vector_store()
    results = {}
    for facility in facilities:
        source = f"ingested_mock_data/pdfs/facility_{facility.lower()}.pdf"
        for document in store.similarity_search(question, k=2, filter={"source": source}):
            add_document(results, document)
    shared = [source for source in SOURCES if "/facility_" not in source]
    for document in store.similarity_search(question, k=4, filter={"source": {"$in": shared}}):
        add_document(results, document)
    return sorted(results.values(), key=lambda d: (d["source"], d["page"], d["id"]))


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

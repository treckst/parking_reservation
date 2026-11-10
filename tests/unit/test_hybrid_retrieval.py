"""Actual BM25 and rank fusion with a mocked dense backend; no providers."""
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from parking.retrieval import create_ensemble, tokenize

SOURCE = "ingested_mock_data/pdfs/booking_policy.pdf"


class Store:
    def __init__(self):
        self.documents = [Document(page_content=text, metadata={"source": SOURCE, "page": page})
            for page, text in enumerate([
                "Electric charging reservations and plugs.",
                "Cancellation cancellation refunds refunds policy.",
                "Accessible entry barriers and opening hours.",
            ])]
        self.filters = []

    def get(self, **kwargs):
        self.filters.append(kwargs["where"])
        return {"ids": [str(i) for i in range(len(self.documents))],
            "documents": [d.page_content for d in self.documents],
            "metadatas": [d.metadata for d in self.documents]}

    def as_retriever(self, *, search_kwargs):
        self.filters.append(search_kwargs["filter"])
        return RunnableLambda(lambda query: [self.documents[0], self.documents[1]])


def test_bm25_dense_fusion_weights_and_identity():
    store = Store()
    retriever = create_ensemble(store, (SOURCE,), 2)
    assert retriever.weights == [0.4, 0.6]
    assert retriever.id_key == "evidence_id"
    assert retriever.retrievers[0].invoke("Cancellation refunds")[0].metadata["page"] == 1
    ids = [d.metadata["evidence_id"] for d in retriever.invoke("Cancellation refunds")]
    assert len(ids) == len(set(ids))
    assert f"{SOURCE}:page:0" in ids and f"{SOURCE}:page:1" in ids
    assert all(f == {"source": {"$in": [SOURCE]}} for f in store.filters)


def test_dense_weight_controls_conflicting_ranks():
    retriever = create_ensemble(Store(), (SOURCE,), 2)
    first, second = retriever.retrievers[0].docs[:2]
    retriever.retrievers = [RunnableLambda(lambda q: [first, second]), RunnableLambda(lambda q: [second, first])]
    assert retriever.invoke("query")[0].metadata["evidence_id"] == second.metadata["evidence_id"]


def test_unicode_tokenization():
    assert tokenize("PARKING, José!") == ["parking", "josé"]


def test_unapproved_metadata_is_excluded():
    store = Store()
    store.documents = [Document(page_content="Private", metadata={"source": "private.pdf", "page": 0})]
    assert create_ensemble(store, (SOURCE,), 2) is None

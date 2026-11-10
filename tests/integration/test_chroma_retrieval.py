"""Read existing embeddings to exercise real Chroma without an OpenAI call."""

import os

import pytest


@pytest.mark.deployed
def test_read_only_chroma_source_identity(external_prerequisite):
    external_prerequisite(os.getenv("TEST_CHROMA_HOST"), "Set TEST_CHROMA_HOST for explicit external corpus checks")
    import chromadb

    client = chromadb.HttpClient(host=os.environ["TEST_CHROMA_HOST"], port=int(os.getenv("TEST_CHROMA_PORT", "8000")))
    collection = client.get_collection("parking_documents")
    before = collection.get(include=["metadatas"])
    count = collection.count()
    source = "ingested_mock_data/pdfs/facility_ctr.pdf"
    record = collection.get(ids=[f"{source}:page:0"], include=["embeddings", "metadatas"])
    assert record["ids"] == [f"{source}:page:0"]
    # Mock the provider embedding with an already stored page vector. This proves
    # real collection query/identity, not semantic quality for a fresh question.
    result = collection.query(query_embeddings=[record["embeddings"][0].tolist()], n_results=2, where={"source": source})
    assert f"{source}:page:0" in result["ids"][0]
    assert collection.count() == count
    assert collection.get(include=["metadatas"]) == before

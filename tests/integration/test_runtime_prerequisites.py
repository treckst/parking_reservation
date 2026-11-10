"""Read-only prerequisite gates for the exact requested runtime and corpus."""

import ast
import importlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import sys

import pytest
from pydantic import BaseModel, ConfigDict


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("module", ["numpy", "chromadb", "langchain_openai", "langgraph.checkpoint.sqlite", "langgraph_sdk", "fastapi"])
def test_runtime_imports(module):
    importlib.import_module(module)


@pytest.mark.parametrize("package,expected", [
    ("chromadb", "1.5.9"),
    ("langgraph-checkpoint-sqlite", "3.1.3"),
    ("langgraph-sdk", "0.4.14"),
    ("langgraph-cli", "0.4.42"),
    ("langgraph-checkpoint-conformance", "0.0.2"),
    ("fastapi", "0.162.2"),
    ("uvicorn", "0.54.0"),
    ("pytest", "9.2.0"),
    ("pytest-asyncio", "1.4.1.post1"),
    ("httpx", "0.28.1"),
])
def test_runtime_versions(package, expected):
    assert version(package) == expected


def test_project_python():
    assert sys.version_info[:2] == (3, 12)


def test_tests_do_not_import_operational_seeds():
    forbidden = {"seed_database", "seed_vector_ingest", "generate_pdfs"}
    for path in (ROOT / "tests").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""] + [alias.name for alias in node.names]
            assert not any(part in forbidden for name in modules for part in name.split(".")), path


class ProbeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str


@pytest.mark.live_model
def test_exact_model_structured_response(external):
    from langchain_openai import ChatOpenAI

    external("OPENAI_API_KEY")
    model = ChatOpenAI(model="gpt-6-luna", use_responses_api=True, timeout=30, max_retries=0)
    structured = model.with_structured_output(ProbeAnswer, method="json_schema", strict=True, include_raw=True)
    try:
        result = structured.invoke("Reply with answer set to parking-runtime-ok.")
    except Exception as exc:
        # Never print provider response bodies or credentials in prerequisite evidence.
        pytest.fail(f"Exact model access/structured-output probe failed: {type(exc).__name__}", pytrace=False)
    assert result["parsing_error"] is None, "Structured output could not be parsed"
    assert isinstance(result["parsed"], ProbeAnswer), "Model refused or returned an incomplete response"
    assert result["parsed"].answer == "parking-runtime-ok"
    assert not result["raw"].additional_kwargs.get("refusal"), "Model refused the probe"


@pytest.mark.live_model
def test_preserved_embedding_compatibility(external):
    """Re-embed a stored page and compare its vector; dimensions alone cannot pass."""
    import chromadb
    from langchain_openai import OpenAIEmbeddings

    external("OPENAI_API_KEY")
    embedding_model = external("PARKING_EMBEDDING_MODEL")
    provenance_path = Path(external("PARKING_EMBEDDING_PROVENANCE"))
    assert provenance_path.is_file(), "Embedding provenance file does not exist"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance.get("model") == embedding_model
    assert provenance.get("collection") == "parking_documents"
    assert provenance.get("evidence"), "Record ingestion evidence or reviewed vector comparison, not dimensions alone"
    assert provenance.get("reviewed_queries"), "Record reviewed queries with expected source/page identities"
    client = chromadb.HttpClient(host=os.getenv("CHROMA_HOST", "127.0.0.1"), port=int(os.getenv("CHROMA_PORT", "8000")))
    collection = client.get_collection("parking_documents")
    stored = collection.get(limit=1, include=["documents", "embeddings", "metadatas"])
    assert len(stored["ids"]) == 1 and stored["documents"][0].strip()
    embeddings = OpenAIEmbeddings(model=embedding_model, check_embedding_ctx_length=False, request_timeout=30, max_retries=0)
    vector = embeddings.embed_query(stored["documents"][0])
    original = stored["embeddings"][0]
    assert len(vector) == len(original)
    similarity = sum(a * b for a, b in zip(vector, original)) / math.sqrt(sum(a * a for a in vector) * sum(b * b for b in original))
    assert similarity >= 0.999, "Stored-page vector differs from the selected embedding model"
    for case in provenance["reviewed_queries"]:
        result = collection.query(query_embeddings=[embeddings.embed_query(case["query"])], n_results=case.get("k", 4), include=["metadatas"])
        citations = {(item["source"], item["page"]) for item in result["metadatas"][0]}
        assert (case["source"], case["page"]) in citations

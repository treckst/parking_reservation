"""Offline dependency and import checks; provider calls are mocked in unit tests."""

import ast
import importlib
from importlib.metadata import version
from pathlib import Path
import sys

import pytest


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

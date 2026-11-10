"""External checks are opt-in; required external checks must never skip."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser):
    parser.addoption("--require-external", action="store_true", default=False)


@pytest.fixture
def external(request):
    if not request.config.getoption("--require-external"):
        pytest.skip("Use --require-external to run external prerequisite checks")
    load_dotenv(ROOT / ".env", override=False)

    def require(name):
        value = os.getenv(name, "").strip()
        if not value or value.startswith("sk-mock-"):
            pytest.fail(f"Required external configuration is missing: {name}", pytrace=False)
        return value

    return require


@pytest.fixture
def isolated_storage(tmp_path):
    """Application tests get their own files, never the booking fixture."""
    return {"checkpoint": tmp_path / "checkpoints.sqlite3", "registry": tmp_path / "registry.sqlite3"}

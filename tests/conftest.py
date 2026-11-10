"""Shared isolated storage for application tests."""

import pytest


def pytest_addoption(parser):
    parser.addoption("--require-external", action="store_true", help="Fail instead of skipping missing external prerequisites")


@pytest.fixture
def external_prerequisite(request):
    def require(condition, reason):
        if not condition:
            if request.config.getoption("--require-external"):
                pytest.fail(reason)
            pytest.skip(reason)
    return require


@pytest.fixture
def isolated_storage(tmp_path):
    """Application tests get their own files, never the booking fixture."""
    return {"checkpoint": tmp_path / "checkpoints.sqlite3", "registry": tmp_path / "registry.sqlite3"}

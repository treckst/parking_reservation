"""Shared isolated storage for application tests."""

import pytest


@pytest.fixture
def isolated_storage(tmp_path):
    """Application tests get their own files, never the booking fixture."""
    return {"checkpoint": tmp_path / "checkpoints.sqlite3", "registry": tmp_path / "registry.sqlite3"}

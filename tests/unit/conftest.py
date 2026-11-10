"""Unit tests never read provider credentials or contact external services."""

import socket

import pytest


@pytest.fixture(autouse=True)
def prevent_external_requests(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("Network access is disabled in unit tests; mock provider calls")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)

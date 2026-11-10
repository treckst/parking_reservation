"""Unit tests never read provider credentials or contact external services."""

import socket

import pytest


@pytest.fixture(autouse=True)
def prevent_external_requests(monkeypatch, _function_scoped_runner):
    # Windows initializes asyncio's local socketpair before the network guard.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("Network access is disabled in unit tests; mock provider calls")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)

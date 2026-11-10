"""Crash boundaries and thread contention independent of provider/network access."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from parking.api.gateway import Gateway
from parking.api.sessions import Conflict, Registry
from parking.api.submissions import Submissions
from parking.settings import Settings


def setup(tmp_path):
    registry = Registry(tmp_path / "registry.db")
    owner = registry.owner(None)
    thread_id = str(uuid4())
    registry.bind_thread(owner, thread_id)
    ledger = Submissions(registry)
    settings = Settings(checkpoint_path=tmp_path / "checkpoints.db", application_path=registry.path)
    client = SimpleNamespace(runs=SimpleNamespace(create=AsyncMock(), list=AsyncMock(), get=AsyncMock()), threads=SimpleNamespace(get_state=AsyncMock()))
    return registry, owner, thread_id, ledger, Gateway(settings, ledger, client)


def test_durable_contention_and_payload_conflict(tmp_path):
    registry, owner, thread_id, ledger, gateway = setup(tmp_path)
    ledger.reserve(owner, thread_id, "request_00000001", "Hours?")
    second = Submissions(Registry(registry.path))
    with pytest.raises(Conflict):
        second.reserve(owner, thread_id, "request_00000002", "Pricing?")
    with pytest.raises(Conflict):
        second.reserve(owner, thread_id, "request_00000001", "Changed")
    assert second.reserve(owner, thread_id, "request_00000001", "Hours?")["status"] == "reserved"


@pytest.mark.asyncio
async def test_lost_ack_reconciles_without_second_create(tmp_path):
    registry, owner, thread_id, ledger, gateway = setup(tmp_path)
    gateway.client.runs.create.side_effect = TimeoutError()
    with pytest.raises(TimeoutError):
        await gateway.submit(owner, thread_id, "request_00000001", "Hours?")
    row = ledger.get(owner, thread_id, "request_00000001")
    gateway.client.runs.list.return_value = [{"run_id": "accepted-run", "metadata": {"request_id": row["request_id"], "payload_fingerprint": row["fingerprint"]}}]
    gateway.client.runs.get.return_value = {"status": "pending"}
    result = await gateway.submit(owner, thread_id, "request_00000001", "Hours?")
    assert result["status"] == "pending"
    assert gateway.client.runs.create.await_count == 1
    assert ledger.get(owner, thread_id, row["request_id"])["run_id"] == "accepted-run"


@pytest.mark.asyncio
async def test_no_matching_run_retains_uncertainty(tmp_path):
    registry, owner, thread_id, ledger, gateway = setup(tmp_path)
    row = ledger.reserve(owner, thread_id, "request_00000001", "Hours?")
    ledger.transition(row, "reserved", "acceptance_unknown")
    gateway.client.runs.list.return_value = []
    result = await gateway.submit(owner, thread_id, row["request_id"], "Hours?")
    assert result["status"] == "pending" and not result["retryable"]
    gateway.client.runs.create.assert_not_awaited()

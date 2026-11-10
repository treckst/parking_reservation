"""The actual synchronous saver must satisfy the server's async contract."""

import asyncio
from uuid import uuid4

from langgraph.checkpoint.conformance import checkpointer_test, validate
import pytest

from parking.checkpoint import generate_checkpointer


@pytest.mark.asyncio
async def test_official_base_conformance(tmp_path):
    @checkpointer_test(name="ParkingSqliteSaver")
    async def factory():
        async with generate_checkpointer(tmp_path / f"{uuid4()}.sqlite3") as saver:
            yield saver

    report = await validate(factory)
    report.print_report()
    assert report.passed_all_base()

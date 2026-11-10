"""The actual synchronous saver must satisfy the server's async contract."""

import asyncio
from copy import deepcopy
import sqlite3
import threading
from typing import TypedDict
from uuid import uuid4

from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.conformance import checkpointer_test, validate
from langgraph.graph import END, START, StateGraph
import pytest

from parking.checkpoint import generate_checkpointer
from parking.settings import Settings


@pytest.mark.asyncio
async def test_official_base_conformance(tmp_path):
    @checkpointer_test(name="ParkingSqliteSaver")
    async def factory():
        async with generate_checkpointer(tmp_path / f"{uuid4()}.sqlite3") as saver:
            yield saver

    report = await validate(factory)
    report.print_report()
    assert report.passed_all_base()
    assert all(report.results[operation].detected for operation in ["put", "put_writes", "get_tuple", "list", "delete_thread"])


@pytest.mark.asyncio
async def test_concurrent_threads_and_restart(tmp_path):
    class State(TypedDict):
        value: int

    builder = StateGraph(State)
    builder.add_node("increment", lambda state: {"value": state["value"] + 1})
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)
    configs = [{"configurable": {"thread_id": name}} for name in ["first", "second"]]
    original_configs = deepcopy(configs)
    path = tmp_path / "checkpoints.sqlite3"
    async with generate_checkpointer(path) as saver:
        graph = builder.compile(checkpointer=saver)
        answers = await asyncio.gather(*(graph.ainvoke({"value": value}, config) for value, config in zip([10, 20], configs)))
        assert answers == [{"value": 11}, {"value": 21}]
        assert configs == original_configs
    async with generate_checkpointer(path) as saver:
        graph = builder.compile(checkpointer=saver)
        assert (await graph.aget_state(configs[0])).values == {"value": 11}
        assert (await graph.aget_state(configs[1])).values == {"value": 21}
        assert len([item async for item in graph.aget_state_history(configs[0])]) >= 2
        await saver.adelete_thread("first")
        assert await saver.aget_tuple(configs[0]) is None
        assert (await graph.aget_state(configs[1])).values == {"value": 21}


@pytest.mark.asyncio
async def test_cancelled_write_drains_before_connection_closes(tmp_path, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    completed = threading.Event()
    async with generate_checkpointer(tmp_path / "checkpoint.sqlite3") as saver:
        connection = saver.saver.conn
        put = saver.saver.put

        def slow_put(*args):
            started.set()
            assert release.wait(timeout=5)
            result = put(*args)
            completed.set()
            return result

        monkeypatch.setattr(saver.saver, "put", slow_put)
        writing = asyncio.create_task(saver.aput({"configurable": {"thread_id": "cancelled", "checkpoint_ns": ""}}, empty_checkpoint(), {}, {}))
        assert await asyncio.to_thread(started.wait, 2)
        writing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await writing

        async def release_write():
            await asyncio.sleep(0.02)
            release.set()

        releasing = asyncio.create_task(release_write())
    await releasing
    assert completed.is_set()
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
    with pytest.raises(RuntimeError, match="closed"):
        await saver.aget_tuple({"configurable": {"thread_id": "cancelled"}})


@pytest.mark.parametrize("collision", ["checkpoint", "registry"])
def test_storage_cannot_overwrite_booking_fixture(tmp_path, collision):
    booking = tmp_path / "booking.sqlite3"
    checkpoint = booking if collision == "checkpoint" else tmp_path / "checkpoint.sqlite3"
    registry = booking if collision == "registry" else tmp_path / "registry.sqlite3"
    with pytest.raises(ValueError, match="separate files"):
        Settings(checkpoint, registry, booking)


def test_checkpoint_and_registry_must_be_separate(tmp_path):
    with pytest.raises(ValueError, match="separate files"):
        Settings(tmp_path / "shared.sqlite3", tmp_path / "shared.sqlite3", tmp_path / "booking.sqlite3")

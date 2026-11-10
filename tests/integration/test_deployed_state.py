"""Operator-only checkpoint inspection of a configured disposable deployment."""

import os
from pathlib import Path
import sqlite3

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver


@pytest.mark.deployed
def test_deployed_two_query_evidence_and_messages(external_prerequisite):
    external_prerequisite(os.getenv("TEST_CHECKPOINT_PATH") and os.getenv("TEST_THREAD_ID"), "Set disposable TEST_CHECKPOINT_PATH and TEST_THREAD_ID after the two-turn journey")
    path = Path(os.environ["TEST_CHECKPOINT_PATH"]).resolve()
    assert "ingested_mock_data" not in path.parts
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False) as db:
        # The deployed file must already contain its schema; avoid saver.setup writes.
        saver = SqliteSaver(db)
        saver.is_setup = True
        record = saver.get_tuple({"configurable": {"thread_id": os.environ["TEST_THREAD_ID"], "checkpoint_ns": ""}})
        assert record is not None
        values = record.checkpoint["channel_values"]
        assert len(values["queries"]) >= 2
        assert {"1:1", "2:1"} <= set(values["evidence"])
        assert len(values["messages"]) >= 4

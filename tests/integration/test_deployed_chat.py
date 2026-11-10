"""Opt-in external journey; the operator must configure a mocked provider endpoint."""

import os
from pathlib import Path
import sqlite3
import subprocess
import time
from uuid import uuid4

import httpx
import pytest


@pytest.mark.deployed
def test_sdk_api_and_separate_checkpoint_restart(external_prerequisite):
    external_prerequisite(os.getenv("TEST_API_URL"), "Set TEST_API_URL to an isolated test API")
    external_prerequisite(os.getenv("TEST_CHECKPOINT_PATH"), "Set TEST_CHECKPOINT_PATH to the graph's mounted test-only file")
    external_prerequisite(os.getenv("TEST_PROVIDER_MOCKED") == "1", "Use a test deployment with mocked OpenAI provider; no paid provider calls")
    external_prerequisite(os.getenv("TEST_ALLOW_GRAPH_RESTART") == "1", "Explicitly permit restart of this test graph service")
    path = Path(os.environ["TEST_CHECKPOINT_PATH"]).resolve()
    assert "ingested_mock_data" not in path.parts
    root = Path(__file__).resolve().parents[2]
    with httpx.Client(base_url=os.environ["TEST_API_URL"], timeout=30) as client:
        thread = client.post("/api/threads").raise_for_status().json()["thread_id"]

        def submit(message):
            request_id = str(uuid4())
            response = client.post("/api/chat", json={"thread_id": thread, "request_id": request_id, "message": message})
            response.raise_for_status()
            result = response.json()
            deadline = time.monotonic() + 90
            while result["status"] == "pending" and time.monotonic() < deadline:
                time.sleep(1)
                result = client.get(f"/api/threads/{thread}/requests/{request_id}").raise_for_status().json()
            assert result["status"] == "completed"
            assert set(result["reply"]) == {"request_id", "final_reply", "reservation_state"}
            assert "p. " in result["reply"]["final_reply"]
            return result

        first = submit("What are CTR opening hours in November 2026?")
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
            assert db.execute("SELECT count(*) FROM checkpoints WHERE thread_id=?", (thread,)).fetchone()[0] > 0
        subprocess.run(["docker", "compose", "-f", str(root / "docker/compose.yaml"), "restart", "graph"], check=True, timeout=60, capture_output=True)
        deadline = time.monotonic() + 90
        while True:
            try:
                if httpx.get(os.getenv("TEST_GRAPH_URL", "http://127.0.0.1:8123") + "/ok", timeout=3).is_success:
                    break
            except httpx.HTTPError:
                pass
            assert time.monotonic() < deadline, "Graph did not recover"
            time.sleep(1)
        second = submit("And what are RIV opening hours?")
        restored = client.get(f"/api/threads/{thread}/conversation").raise_for_status().json()
        assert len(restored["messages"]) == 4
        assert first["reply"]["reservation_state"] == second["reply"]["reservation_state"]

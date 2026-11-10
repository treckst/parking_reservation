"""Public boundaries, safe responses, and ownership before SDK access."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from parking.api.app import create_app
from parking.settings import Settings


@pytest.fixture
def api(tmp_path):
    sdk = SimpleNamespace(
        threads=SimpleNamespace(create=AsyncMock(side_effect=lambda: {"thread_id": str(uuid4())}), get_state=AsyncMock()),
        runs=SimpleNamespace(create=AsyncMock(return_value={"run_id": "run-1"}), get=AsyncMock(return_value={"status": "pending"}), list=AsyncMock(return_value=[]), join=AsyncMock()),
    )
    settings = Settings(checkpoint_path=tmp_path / "checkpoints.db", application_path=tmp_path / "registry.db")
    app = create_app(settings, sdk)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, sdk, app


def test_cross_owner_routes_never_touch_sdk(api):
    client, sdk, app = api
    thread_id = client.post("/api/threads").json()["thread_id"]
    sdk.threads.create.reset_mock()
    with TestClient(app, raise_server_exceptions=False) as stranger:
        assert stranger.get(f"/api/threads/{thread_id}/conversation").status_code == 404
        assert stranger.get(f"/api/threads/{thread_id}/requests/request_00000001").status_code == 404
        assert stranger.post("/api/chat", json={"thread_id": thread_id, "request_id": "request_00000001", "message": "Hours?"}).status_code == 404
    sdk.runs.create.assert_not_awaited()
    sdk.runs.get.assert_not_awaited()
    sdk.runs.list.assert_not_awaited()


@pytest.mark.parametrize("message", [None, "", "  \n ", "a" * 4001])
def test_invalid_message_has_safe_422(api, message):
    client, sdk, app = api
    response = client.post("/api/chat", json={"thread_id": str(uuid4()), "request_id": "request_00000001", "message": message})
    assert response.status_code == 422
    assert response.json() == {"error_code": "invalid_request"}
    sdk.runs.create.assert_not_awaited()


def test_pending_request_and_idempotent_repeat(api):
    client, sdk, app = api
    thread_id = client.post("/api/threads").json()["thread_id"]
    payload = {"thread_id": thread_id, "request_id": "request_00000001", "message": "Godziny? 🚗"}
    assert client.post("/api/chat", json=payload).status_code == 202
    assert client.post("/api/chat", json=payload).status_code == 202
    assert sdk.runs.create.await_count == 1
    assert client.post("/api/chat", json={**payload, "message": "Different"}).status_code == 409
    assert client.post("/api/chat", json={**payload, "request_id": "request_00000002"}).status_code == 409


def test_completed_dto_drops_raw_state(api):
    client, sdk, app = api
    thread_id = client.post("/api/threads").json()["thread_id"]
    sdk.runs.get.return_value = {"status": "success"}
    sdk.threads.get_state.return_value = {"values": {
        "request_id": "request_00000001", "final_reply": "Open daily. [Booking policy, p. 1]",
        "reservation_state": {}, "candidate": "PRIVATE_CANARY", "evidence": {"private": "SECRET"},
    }}
    response = client.post("/api/chat", json={"thread_id": thread_id, "request_id": "request_00000001", "message": "Hours?"})
    assert response.status_code == 200
    assert "PRIVATE_CANARY" not in response.text and "SECRET" not in response.text
    restored = client.get(f"/api/threads/{thread_id}/conversation").json()
    assert [m["role"] for m in restored["messages"]] == ["user", "assistant"]


def test_foreign_origin_denied(api):
    client, sdk, app = api
    response = client.post("/api/threads", headers={"Origin": "https://attacker.example"})
    assert response.status_code == 403
    sdk.threads.create.assert_not_awaited()


def test_ui_assets_and_health_do_not_require_graph_calls(api):
    client, sdk, app = api
    with app.state.registry.connection() as db:
        before = db.execute("SELECT count(*) FROM owners").fetchone()[0]
    assert client.get("/health").json() == {"ok": True}
    with app.state.registry.connection() as db:
        assert db.execute("SELECT count(*) FROM owners").fetchone()[0] == before
    assert 'id="composer"' in client.get("/").text
    assert client.get("/app.mjs").status_code == 200
    assert client.get("/styles.css").status_code == 200
    sdk.runs.create.assert_not_awaited()

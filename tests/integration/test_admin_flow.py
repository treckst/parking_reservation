"""Real nested graph, durable SQLite restart, mocked provider and remote SDK."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from langchain_core.messages import AIMessage

from parking.api.app import create_app
from parking.api.sessions import Conflict
from parking.bookings import BookingStore
from parking.graph.graph import build_graph
from parking.graph.schemas import AdminDecision, Intent, ReservationExtraction, ReservationDraft, ReservationSummary
from tests.extraction_helpers import updates
from parking.settings import Settings
from tests.unit.test_policy_flow import DOCUMENT, Model


DRAFT = {"spot_id": "CTR-001", "start": "2026-11-20T08:00:00+01:00",
         "end": "2026-11-20T10:00:00+01:00", "name": "PrivateName",
         "surname": "PrivateSurname", "car_number": "PRIVATE_PLATE"}


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "bookings.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE transport_slots (spot_id TEXT, slot_date TEXT, working_hours TEXT,
                                          type TEXT DEFAULT 'standard', hourly_price REAL DEFAULT 8,
                                          current_availability INTEGER DEFAULT 1,
                                          PRIMARY KEY(spot_id,slot_date));
            INSERT INTO transport_slots (spot_id,slot_date,working_hours)
                VALUES ('CTR-001','2026-11-20','06:00-22:00');
            INSERT INTO transport_slots (spot_id,slot_date,working_hours,hourly_price)
                VALUES ('AIR-001','2026-11-13','06:00-22:00',5);
            CREATE TABLE reservations (spot_id TEXT,start_time TEXT,end_time TEXT,status TEXT);
        """)
    return BookingStore(path)


class BookingModel(Model):
    def __init__(self, response="approve", draft=None):
        super().__init__()
        self.response = response
        self.draft = DRAFT if draft is None else draft

    def bind_tools(self, tools, **kwargs):
        assert kwargs == {"parallel_tool_calls": False}
        assert {tool.name for tool in tools} == {"inspect_reservation_draft", "update_reservation_draft",
                                               "ask_missing_reservation_details", "submit_reservation_draft"}
        model = self

        class Bound:
            async def ainvoke(self, messages):
                last = messages[-1]
                args = {}
                if last.type == "human":
                    name = "inspect_reservation_draft"
                elif last.name == "inspect_reservation_draft":
                    name, args = "update_reservation_draft", {"updates": updates({key: value for key, value in model.draft.items()
                        if key not in ("start", "end")})}
                    model.calls["draft"] += 1
                else:
                    name = ("submit_reservation_draft" if json.loads(last.content)["ready"] else
                            "ask_missing_reservation_details")
                return AIMessage(content="", tool_calls=[{"name": name, "args": args,
                    "id": str(uuid4()), "type": "tool_call"}])

        return Bound()

    def with_structured_output(self, schema, **kwargs):
        base = super().with_structured_output(schema, **kwargs)
        model = self

        class Structured:
            async def ainvoke(self, messages):
                data = json.loads(messages[-1].content)
                if schema is Intent and data["message"].startswith("Book"):
                    return {"kind": "reservation", "language": "en", "facilities": ["CTR"],
                            "retrieval_question": data["message"]}
                if schema is ReservationDraft:
                    model.calls["draft"] += 1
                    return model.draft
                if schema is ReservationExtraction:
                    return {"updates": updates(model.extraction_draft if hasattr(model, "extraction_draft") else model.draft)}
                if schema is ReservationSummary:
                    return {"summary": "Request CTR-001 on November 20, 08:00-10:00."}
                if schema is AdminDecision:
                    model.calls["review"] += 1
                    assert "administrator_response" in data
                    return {"response": model.response}
                return await base.ainvoke(messages)

        return Structured()


@pytest.mark.parametrize("decision,status", [("approve", "approved"), ("reject", "rejected")])
async def test_nested_pause_restart_resume_preserves_state(store, tmp_path, decision, status):
    model = BookingModel(decision)
    config = {"configurable": {"thread_id": "owned-thread"}}
    checkpoint = str(tmp_path / "checkpoint.sqlite3")
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: model, lambda q, f: [DOCUMENT], checkpointer=saver, booking_store=store)
        await graph.ainvoke({"message": "Hours?", "request_id": "policy_000000001"}, config)
        before = (await graph.aget_state(config)).values
        paused = await graph.ainvoke({"message": "Book my spot", "request_id": "booking_00000001"}, config)
        assert paused["__interrupt__"]
        state = (await graph.aget_state(config)).values
        reservation_id = state["reservation_id"]
        assert store.get(reservation_id)["status"] == "pending"
        assert store.get(reservation_id)["summary"] == state["reservation_summary"]
        assert state["booking_draft"] == json.loads(store.get(reservation_id)["draft"])
        assert model.calls["review"] == 0
        assert all(state["evidence"][key] == value for key, value in before["evidence"].items())
        assert state["evidence"]["2:1"]["sql_results"]
        assert len(state["messages"]) == 3
        assert store.claim_review(reservation_id, decision)
    # New saver/compiled graph: no process-local graph state is required.
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: model, lambda q, f: [DOCUMENT], checkpointer=saver, booking_store=store)
        output = await graph.ainvoke(Command(resume={"reservation_id": reservation_id, "response": decision}), config)
        assert store.get(reservation_id)["status"] == status
        state = (await graph.aget_state(config)).values
        assert state["admin_result"] == {"reservation_id": reservation_id, "status": status, "reason": None}
        assert not {"admin_decision", "admin_response", "admin_messages"} & state.keys()
        assert ("approved" if decision == "approve" else "rejected") in output["final_reply"]
        assert all(state["evidence"][key] == value for key, value in before["evidence"].items())
        assert set(state["queries"]) == {"policy_000000001", "booking_00000001"}
        assert len(state["messages"]) == 4
        assert model.calls["draft"] == model.calls["review"] == 1
        assert "Private" not in json.dumps(output)
        assert set(output) == {"request_id", "final_reply", "reservation_state"}
        await graph.ainvoke(None, config)
        assert model.calls["review"] == 1


async def test_incomplete_draft_does_not_hold_or_interrupt(store, tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver

    model = BookingModel(draft={})
    graph = build_graph(lambda: model, checkpointer=InMemorySaver(), booking_store=store)
    result = await graph.ainvoke({"message": "Book a spot", "request_id": "booking_00000001"},
                               {"configurable": {"thread_id": "thread"}})
    assert "__interrupt__" not in result
    assert "Please provide" in result["final_reply"]
    assert not store.pending()


@pytest.mark.parametrize("bad_resume", ["unclaimed", "wrong_reservation", "invalid_output"])
async def test_resume_cannot_bypass_admin_boundary(store, bad_resume):
    from langgraph.checkpoint.memory import InMemorySaver

    model = BookingModel("not-a-decision" if bad_resume == "invalid_output" else "approve")
    config = {"configurable": {"thread_id": "thread"}}
    graph = build_graph(lambda: model, checkpointer=InMemorySaver(), booking_store=store)
    await graph.ainvoke({"message": "Book my spot", "request_id": "booking_00000001"}, config)
    reservation_id = (await graph.aget_state(config)).values["reservation_id"]
    if bad_resume != "unclaimed":
        store.claim_review(reservation_id, "approve")
    with pytest.raises(ValueError):
        await graph.ainvoke(Command(resume={
            "reservation_id": "another-reservation" if bad_resume == "wrong_reservation" else reservation_id,
            "response": "approve"}), config)
    assert store.get(reservation_id)["status"] == "pending"


def test_pending_holds_are_atomic_and_rejection_releases(store):
    def reserve(index):
        try:
            return store.reserve(f"thread-{index}", "request", DRAFT, "Intent")
        except ValueError as error:
            return str(error)
    # Initialize schema before contention, using independent connections per writer.
    store.pending()
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(reserve, range(2)))
    rows = [r for r in results if isinstance(r, dict)]
    assert len(rows) == 1 and "slot_unavailable" in results
    row = rows[0]
    assert store.reserve(row["thread_id"], "request", DRAFT, "Intent")["reservation_id"] == row["reservation_id"]
    store.decide(row["reservation_id"], False)
    assert store.reserve("another", "request", DRAFT, "Intent")["status"] == "pending"
    with pytest.raises(Conflict):
        store.decide(row["reservation_id"], True)


def test_legacy_overlap_and_adjacent_interval(store):
    with sqlite3.connect(store.path) as db:
        db.execute("INSERT INTO reservations VALUES (?,?,?,'confirmed')",
                   (DRAFT["spot_id"], DRAFT["start"], DRAFT["end"]))
    with pytest.raises(ValueError, match="slot_unavailable"):
        store.reserve("thread", "request", DRAFT, "Intent")
    row = store.reserve("thread", "request", {**DRAFT, "start": DRAFT["end"],
                       "end": "2026-11-20T11:00:00+01:00"}, "Intent")
    assert row["status"] == "pending"


@pytest.mark.parametrize("change,reason", [("conflict", "slot_unavailable"), ("hours", "outside_hours")])
async def test_admin_tool_revalidates_before_approval(store, change, reason):
    from langgraph.checkpoint.memory import InMemorySaver

    model = BookingModel()
    config = {"configurable": {"thread_id": "thread"}}
    graph = build_graph(lambda: model, checkpointer=InMemorySaver(), booking_store=store)
    await graph.ainvoke({"message": "Book my spot", "request_id": "booking_00000001"}, config)
    reservation_id = (await graph.aget_state(config)).values["reservation_id"]
    with sqlite3.connect(store.path) as db:
        if change == "conflict":
            db.execute("INSERT INTO reservations VALUES (?,?,?,'confirmed')",
                       (DRAFT["spot_id"], DRAFT["start"], DRAFT["end"]))
        else:
            db.execute("UPDATE transport_slots SET working_hours='10:00-22:00'")
    store.claim_review(reservation_id, "approve")
    result = await graph.ainvoke(Command(resume={"reservation_id": reservation_id, "response": "approve"}), config)
    state = (await graph.aget_state(config)).values
    assert state["admin_result"] == {"reservation_id": reservation_id, "status": "rejected", "reason": reason}
    assert "rejected" in result["final_reply"] and "Private" not in json.dumps(result)
    assert store.decide(reservation_id, True)["status"] == "rejected"


def test_approved_row_is_same_record_and_replay_safe(store):
    row = store.reserve("thread", "request", DRAFT, "Intent")
    approved = store.decide(row["reservation_id"], True)
    assert approved == {**row, "status": "approved"}
    assert store.decide(row["reservation_id"], True) == approved
    with pytest.raises(ValueError, match="slot_unavailable"):
        store.reserve("other-thread", "request", DRAFT, "Intent")
    with pytest.raises(Conflict):
        store.decide(row["reservation_id"], False)


def test_migrate_confirmed_requests_preserves_identity_and_claims(store):
    row = store.reserve("thread", "request", DRAFT, "Intent")
    store.claim_review(row["reservation_id"], "approve")
    store.review_dispatched(row["reservation_id"], "existing-run")
    with sqlite3.connect(store.path) as db:
        # Recreate the previous application's schema and one confirmed row.
        schema = db.execute("SELECT sql FROM sqlite_master WHERE name='booking_requests'").fetchone()[0]
        db.execute(schema.replace("booking_requests", "old_requests", 1).replace("'approved'", "'confirmed'"))
        db.execute("INSERT INTO old_requests SELECT * FROM booking_requests")
        db.execute("UPDATE old_requests SET status='confirmed'")
        db.execute("DROP TABLE booking_requests")
        db.execute("ALTER TABLE old_requests RENAME TO booking_requests")
        db.execute("ALTER TABLE booking_requests DROP COLUMN decision_reason")
    migrated = store.get(row["reservation_id"])
    assert migrated["status"] == "approved"
    assert migrated["draft"] == row["draft"] and migrated["summary"] == row["summary"]
    assert migrated["review_text"] == "approve" and migrated["review_run_id"] == "existing-run"
    assert store.get(row["reservation_id"]) == migrated
    with pytest.raises(ValueError, match="slot_unavailable"):
        store.reserve("another", "request", DRAFT, "Intent")


async def test_summary_runs_after_pending_write_and_receives_no_pii(store):
    from langgraph.checkpoint.memory import InMemorySaver

    model = BookingModel()

    def factory():
        class CheckedModel:
            def bind_tools(self, tools, **kwargs):
                return model.bind_tools(tools, **kwargs)

            def with_structured_output(self, schema, **kwargs):
                delegate = model.with_structured_output(schema, **kwargs)

                class Structured:
                    async def ainvoke(self, messages):
                        if schema is ReservationSummary:
                            assert len(store.pending()) == 1
                            assert store.pending()[0]["status"] == "pending"
                            assert "Private" not in messages[-1].content
                        return await delegate.ainvoke(messages)

                return Structured()
        return CheckedModel()

    graph = build_graph(factory, checkpointer=InMemorySaver(), booking_store=store)
    output = await graph.ainvoke({"message": "Book my spot", "request_id": "booking_00000001"},
                                {"configurable": {"thread_id": "thread"}})
    assert output["__interrupt__"]


@pytest.fixture
def admin_api(store, tmp_path):
    thread = str(uuid4())
    sdk = SimpleNamespace(
        threads=SimpleNamespace(create=AsyncMock(return_value={"thread_id": thread}), get_state=AsyncMock()),
        runs=SimpleNamespace(create=AsyncMock(return_value={"run_id": "initial"}),
            get=AsyncMock(return_value={"status": "pending"}), list=AsyncMock(return_value=[]), join=AsyncMock()))
    settings = Settings(checkpoint_path=tmp_path / "checkpoint.db", application_path=tmp_path / "registry.db",
                        booking_path=store.path)
    app = create_app(settings, sdk)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post("/api/threads")
        client.post("/api/chat", json={"thread_id": thread, "request_id": "booking_00000001", "message": "Book"})
        row = store.reserve(thread, "booking_00000001", DRAFT, "Request this spot")
        sdk.threads.get_state.return_value = {"next": ["admin"], "values": {
            "reservation_id": row["reservation_id"], "request_id": row["request_id"],
            "evidence": {"SECRET": "PRIVATE"}}}
        sdk.runs.get.return_value = {"status": "interrupted"}
        sdk.runs.create.reset_mock()
        yield client, sdk, app, row


def test_admin_api_and_pending_customer_dto(admin_api):
    client, sdk, app, row = admin_api
    response = client.get(f"/api/threads/{row['thread_id']}/requests/{row['request_id']}")
    assert response.json()["status"] == "pending" and not response.json()["retryable"]
    assert "PRIVATE" not in response.text
    listed = client.get("/api/admin/reservations").json()
    assert listed["reservations"][0]["reservation_id"] == row["reservation_id"]
    assert "PRIVATE_PLATE" not in json.dumps(listed)
    sdk.runs.create.return_value = {"run_id": "continuation"}
    url = f"/api/admin/reservations/{row['reservation_id']}/review"
    assert client.post(url, json={"response": "approve"}).status_code == 202
    assert client.post(url, json={"response": "approve"}).status_code == 202
    assert client.post(url, json={"response": "reject"}).status_code == 409
    assert sdk.runs.create.await_count == 1
    command = sdk.runs.create.call_args.kwargs["command"]
    assert command == {"resume": {"reservation_id": row["reservation_id"], "response": "approve"}}
    sdk.runs.get.return_value = {"status": "success"}
    sdk.threads.get_state.return_value = {"next": [], "values": {
        "request_id": row["request_id"], "final_reply": "Approved.", "reservation_state": {},
        "admin_response": "PRIVATE", "booking_draft": DRAFT}}
    result = client.get(f"/api/threads/{row['thread_id']}/requests/{row['request_id']}")
    assert result.json()["status"] == "completed" and "PRIVATE" not in result.text


def test_admin_lost_ack_reconciles_without_second_resume(admin_api):
    client, sdk, app, row = admin_api
    sdk.runs.create.side_effect = TimeoutError()
    url = f"/api/admin/reservations/{row['reservation_id']}/review"
    assert client.post(url, json={"response": "approve"}).status_code == 503
    sdk.runs.list.return_value = [{"run_id": "lost-ack-run", "metadata": {"admin_review_id": row["reservation_id"]}}]
    result = client.post(url, json={"response": "approve"})
    assert result.status_code == 202 and result.json()["dispatch_status"] == "accepted"
    assert sdk.runs.create.await_count == 1


def test_review_rejects_wrong_checkpoint_and_bad_input(admin_api):
    client, sdk, app, row = admin_api
    sdk.threads.get_state.return_value = {"next": [], "values": {}}
    url = f"/api/admin/reservations/{row['reservation_id']}/review"
    assert client.post(url, json={"response": "approve"}).status_code == 409
    assert client.post(url, json={"response": " "}).status_code == 422
    assert client.post(url, json={"response": "approve"}, headers={"Origin": "https://foreign.example"}).status_code == 403
    sdk.runs.create.assert_not_awaited()

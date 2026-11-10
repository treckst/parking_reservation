"""Real nested graph, durable SQLite restart, mocked provider and remote SDK."""

import json
import sqlite3
import asyncio
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
from parking.graph.admin import build_admin_graph
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
            CREATE TABLE reservations (
                reservation_id TEXT PRIMARY KEY NOT NULL,
                spot_id TEXT NOT NULL,
                slot_date TEXT NOT NULL CHECK (slot_date BETWEEN '2026-11-01' AND '2026-11-10'),
                name TEXT NOT NULL,
                surname TEXT NOT NULL,
                car_number TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL CHECK (end_time > start_time),
                status TEXT NOT NULL CHECK (status IN ('confirmed','active','completed','cancelled')),
                created_at TEXT NOT NULL CHECK (created_at <= start_time),
                CHECK (substr(start_time,1,10)=slot_date),
                CHECK (substr(end_time,1,10)=slot_date),
                FOREIGN KEY (spot_id,slot_date) REFERENCES transport_slots (spot_id,slot_date)
            );
            CREATE INDEX reservations_spot_time ON reservations (spot_id,start_time,end_time);
        """)
    return BookingStore(path)


def insert_legacy_reservation(store, reservation_id="legacy", draft=DRAFT):
    store.pending()  # Apply the fixture date-range migration before inserting a November 11-30 row.
    with sqlite3.connect(store.path) as db:
        db.execute("""INSERT INTO reservations
            (reservation_id,spot_id,slot_date,name,surname,car_number,start_time,end_time,status,created_at)
            VALUES (?,?,?,?,?,?,?,?, 'confirmed',?)""",
            (reservation_id, draft["spot_id"], draft["start"][:10], draft["name"], draft["surname"],
             draft["car_number"], draft["start"].replace("T", " "), draft["end"].replace("T", " "),
             "2026-11-09 12:00:00+01:00"))


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
                    assert set(data) == {"booking_draft", "reservation_summary"}
                    assert data["booking_draft"]["spot_id"] and data["reservation_summary"]
                    if isinstance(model.response, Exception):
                        raise model.response
                    return {"response": model.response}
                return await base.ainvoke(messages)

        return Structured()


@pytest.mark.parametrize("decision,status", [("approve", "approved"), ("reject", "rejected")])
async def test_automatic_nested_review_and_restart_preserves_state(store, tmp_path, decision, status):
    model = BookingModel(decision)
    config = {"configurable": {"thread_id": "owned-thread"}}
    checkpoint = str(tmp_path / "checkpoint.sqlite3")
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: model, lambda q, f: [DOCUMENT], checkpointer=saver, booking_store=store)
        await graph.ainvoke({"message": "Hours?", "request_id": "policy_000000001"}, config)
        before = (await graph.aget_state(config)).values
        output = await graph.ainvoke({"message": "Book my spot", "request_id": "booking_00000001"}, config)
        assert "__interrupt__" not in output
        state = (await graph.aget_state(config)).values
        reservation_id = state["reservation_id"]
        assert store.get(reservation_id)["status"] == status
        assert store.get(reservation_id)["summary"] == state["reservation_summary"]
        assert state["booking_draft"] == json.loads(store.get(reservation_id)["draft"])
        assert model.calls["review"] == 1
        assert all(state["evidence"][key] == value for key, value in before["evidence"].items())
        assert state["evidence"]["2:1"]["sql_results"]
        assert len(state["messages"]) == 4
    # New saver/compiled graph: no process-local graph state is required.
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: model, lambda q, f: [DOCUMENT], checkpointer=saver, booking_store=store)
        output = await graph.ainvoke(None, config)
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


@pytest.mark.parametrize("fault", ["draft", "summary", "incomplete", "invalid_output", "provider_error"])
async def test_admin_rejects_bad_handoff_or_provider_failure_without_approval(store, fault):
    row = store.reserve("thread", "request", DRAFT, "Request CTR-001 08:00-10:00")
    state = {"reservation_id": row["reservation_id"], "booking_draft": json.loads(row["draft"]),
             "reservation_summary": row["summary"]}
    model = BookingModel(RuntimeError("provider unavailable") if fault == "provider_error" else
                         "not-a-decision" if fault == "invalid_output" else "approve")
    if fault == "draft":
        state["booking_draft"]["car_number"] = "OTHER"
    elif fault == "incomplete":
        state["booking_draft"]["surname"] = None
    elif fault == "summary":
        state["reservation_summary"] = "A different spot and interval"
    graph = build_admin_graph(lambda: model, store).compile()
    with pytest.raises((ValueError, RuntimeError)):
        await graph.ainvoke(state)
    assert store.get(row["reservation_id"])["status"] == "pending"
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT 1 FROM reservations WHERE reservation_id=?", (row["reservation_id"],)).fetchone() is None


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
    insert_legacy_reservation(store)
    with pytest.raises(ValueError, match="slot_unavailable"):
        store.reserve("thread", "request", DRAFT, "Intent")
    row = store.reserve("thread", "request", {**DRAFT, "start": DRAFT["end"],
                       "end": "2026-11-20T11:00:00+01:00"}, "Intent")
    assert row["status"] == "pending"


@pytest.mark.parametrize("change,reason", [("conflict", "slot_unavailable"), ("hours", "outside_hours")])
async def test_admin_tool_revalidates_before_approval(store, change, reason):
    model = BookingModel()
    row = store.reserve("thread", "request", DRAFT, "Request CTR-001 08:00-10:00")
    reservation_id = row["reservation_id"]
    with sqlite3.connect(store.path) as db:
        if change == "conflict":
            db.execute("""INSERT INTO reservations
                (reservation_id,spot_id,slot_date,name,surname,car_number,start_time,end_time,status,created_at)
                VALUES ('legacy',?,?,?,?,?,?,?,'confirmed','2026-11-09 12:00:00+01:00')""",
                (DRAFT["spot_id"], DRAFT["start"][:10], DRAFT["name"], DRAFT["surname"],
                 DRAFT["car_number"], DRAFT["start"].replace("T", " "), DRAFT["end"].replace("T", " ")))
        else:
            db.execute("UPDATE transport_slots SET working_hours='10:00-22:00'")
    graph = build_admin_graph(lambda: model, store).compile()
    result = await graph.ainvoke({"reservation_id": reservation_id,
        "booking_draft": json.loads(row["draft"]), "reservation_summary": row["summary"]})
    assert result["admin_result"] == {"reservation_id": reservation_id, "status": "rejected", "reason": reason}
    assert "Private" not in json.dumps(result)
    assert store.decide(reservation_id, True)["status"] == "rejected"


def test_approved_request_is_promoted_to_one_confirmed_reservation_and_replay_safe(store):
    row = store.reserve("thread", "request", DRAFT, "Intent")
    approved = store.decide(row["reservation_id"], True)
    assert approved == {**row, "status": "approved"}
    assert store.decide(row["reservation_id"], True) == approved
    with sqlite3.connect(store.path) as db:
        reservations = db.execute("SELECT * FROM reservations WHERE reservation_id=?", (row["reservation_id"],)).fetchall()
        assert len(reservations) == 1
        names = [column[1] for column in db.execute("PRAGMA table_info(reservations)")]
        confirmed = dict(zip(names, reservations[0]))
        assert (confirmed["spot_id"], confirmed["slot_date"], confirmed["name"], confirmed["surname"],
                confirmed["car_number"], confirmed["status"]) == (
                    DRAFT["spot_id"], DRAFT["start"][:10], DRAFT["name"], DRAFT["surname"],
                    DRAFT["car_number"], "confirmed")
        assert confirmed["created_at"]
        assert "2026-11-01" not in db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='reservations'").fetchone()[0]
    with pytest.raises(ValueError, match="slot_unavailable"):
        store.reserve("other-thread", "request", DRAFT, "Intent")
    with pytest.raises(Conflict):
        store.decide(row["reservation_id"], False)


def test_approval_insert_failure_rolls_back_request_status(store):
    row = store.reserve("thread", "request", DRAFT, "Intent")
    with sqlite3.connect(store.path) as db:
        db.execute("""CREATE TRIGGER fail_reservation_promotion BEFORE INSERT ON reservations
            BEGIN SELECT RAISE(ABORT, 'forced insert failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="forced insert failure"):
        store.decide(row["reservation_id"], True)
    assert store.get(row["reservation_id"])["status"] == "pending"
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT 1 FROM reservations WHERE reservation_id=?", (row["reservation_id"],)).fetchone() is None


def test_reservations_migration_preserves_existing_fixture_rows(store):
    legacy = {**DRAFT, "start": "2026-11-10T15:00:00+01:00", "end": "2026-11-10T16:00:00+01:00"}
    with sqlite3.connect(store.path) as db:
        db.execute("INSERT INTO transport_slots (spot_id,slot_date,working_hours) VALUES ('CTR-001','2026-11-10','06:00-22:00')")
        db.execute("""INSERT INTO reservations
            (reservation_id,spot_id,slot_date,name,surname,car_number,start_time,end_time,status,created_at)
            VALUES ('legacy-reservation','CTR-001','2026-11-10',?,?,?,?,?,'confirmed','2026-11-09 12:00:00+01:00')""",
            (legacy["name"], legacy["surname"], legacy["car_number"],
             legacy["start"].replace("T", " "), legacy["end"].replace("T", " ")))
    store.pending()  # initializes the additive request table and upgrades the fixture constraint
    with sqlite3.connect(store.path) as db:
        row = db.execute("""SELECT reservation_id,spot_id,slot_date,name,surname,car_number,status
            FROM reservations WHERE reservation_id='legacy-reservation'""").fetchone()
        assert row == ("legacy-reservation", "CTR-001", "2026-11-10", legacy["name"],
                       legacy["surname"], legacy["car_number"], "confirmed")
        schema = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reservations'").fetchone()[0]
        assert "2026-11-10" not in schema


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
    assert "__interrupt__" not in output and "approved" in output["final_reply"]


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
            "evidence": {"SECRET": "PRIVATE"}}, "tasks": [{"name": "admin", "interrupts": [{"value": {
                "kind": "admin_approval", "reservation_id": row["reservation_id"]}}]}]}
        sdk.runs.get.return_value = {"status": "interrupted"}
        sdk.runs.create.reset_mock()
        sdk.runs.create.return_value = {"run_id": "continuation"}
        yield client, sdk, app, row


def test_customer_poll_recovers_old_admin_interrupt_once_and_returns_final_dto(admin_api):
    client, sdk, app, row = admin_api
    response = client.get(f"/api/threads/{row['thread_id']}/requests/{row['request_id']}")
    assert response.json()["status"] == "pending" and not response.json()["retryable"]
    assert "PRIVATE" not in response.text
    listed = client.get("/api/admin/reservations").json()
    assert listed["reservations"][0]["reservation_id"] == row["reservation_id"]
    assert "PRIVATE_PLATE" not in json.dumps(listed)
    url = f"/api/admin/reservations/{row['reservation_id']}/resume"
    assert client.post(url).status_code == 202
    assert client.post(url).status_code == 202
    assert client.post(f"/api/admin/reservations/{row['reservation_id']}/review", json={"response": "approve"}).status_code == 404
    assert sdk.runs.create.await_count == 1
    command = sdk.runs.create.call_args.kwargs["command"]
    assert command == {"resume": {"reservation_id": row["reservation_id"]}}
    sdk.runs.get.return_value = {"status": "success"}
    sdk.threads.get_state.return_value = {"next": [], "values": {
        "request_id": row["request_id"], "final_reply": "Approved.", "reservation_state": {},
        "admin_response": "PRIVATE", "booking_draft": DRAFT}}
    result = client.get(f"/api/threads/{row['thread_id']}/requests/{row['request_id']}")
    assert result.json()["status"] == "completed" and "PRIVATE" not in result.text


def test_admin_lost_ack_reconciles_without_second_resume(admin_api):
    client, sdk, app, row = admin_api
    sdk.runs.create.side_effect = TimeoutError()
    url = f"/api/threads/{row['thread_id']}/requests/{row['request_id']}"
    assert client.get(url).status_code == 503
    sdk.runs.list.return_value = [{"run_id": "lost-ack-run", "metadata": {"admin_review_id": row["reservation_id"]}}]
    # A new API adapter reconnects using durable claims, not in-memory flags.
    from parking.api.admin import AdminGateway
    app.state.gateway.admin = AdminGateway(sdk, app.state.gateway.admin.store, app.state.gateway.submissions)
    result = client.get(url)
    assert result.status_code == 202 and result.json()["status"] == "pending"
    assert app.state.gateway.admin.store.get(row["reservation_id"])["dispatch_status"] == "accepted"
    assert sdk.runs.create.await_count == 1


def test_resume_rejects_wrong_checkpoint_and_cross_origin(admin_api):
    client, sdk, app, row = admin_api
    sdk.threads.get_state.return_value = {"next": [], "values": {}}
    url = f"/api/admin/reservations/{row['reservation_id']}/resume"
    assert client.post(url).status_code == 409
    assert client.post(url, headers={"Origin": "https://foreign.example"}).status_code == 403
    sdk.runs.create.assert_not_awaited()


def test_customer_poll_cannot_resume_a_request_from_another_thread(admin_api):
    client, sdk, app, row = admin_api
    with sqlite3.connect(app.state.gateway.admin.store.path) as db:
        db.execute("UPDATE booking_requests SET thread_id=? WHERE reservation_id=?",
                   (str(uuid4()), row["reservation_id"]))
    result = client.get(f"/api/threads/{row['thread_id']}/requests/{row['request_id']}")
    assert result.status_code == 503 and "PRIVATE" not in result.text
    sdk.runs.create.assert_not_awaited()


async def test_concurrent_legacy_recovery_dispatches_only_once(admin_api):
    client, sdk, app, row = admin_api
    gateway = app.state.gateway.admin
    await asyncio.gather(gateway.reconcile(row), gateway.reconcile(row))
    assert sdk.runs.create.await_count == 1
    assert gateway.store.get(row["reservation_id"])["review_run_id"] == "continuation"


def test_unknown_legacy_resume_acceptance_stays_pending_without_redispatch(admin_api):
    client, sdk, app, row = admin_api
    sdk.runs.create.side_effect = TimeoutError()
    url = f"/api/threads/{row['thread_id']}/requests/{row['request_id']}"
    assert client.get(url).status_code == 503
    result = client.get(url)
    assert result.status_code == 202 and result.json()["status"] == "pending"
    assert sdk.runs.create.await_count == 1
    assert app.state.gateway.admin.store.get(row["reservation_id"])["dispatch_status"] == "creating"


@pytest.mark.parametrize("approved", [True, False])
async def test_automatic_admin_replay_uses_durable_result_without_another_llm_decision(store, approved):
    row = store.reserve("thread", "request", DRAFT, "Request CTR-001 08:00-10:00")
    final = store.decide(row["reservation_id"], approved)
    model = BookingModel("reject" if approved else "approve")
    result = await build_admin_graph(lambda: model, store).compile().ainvoke({
        "reservation_id": row["reservation_id"], "booking_draft": json.loads(row["draft"]),
        "reservation_summary": row["summary"]})
    assert result["admin_result"]["status"] == final["status"]
    assert model.calls["review"] == 0


async def test_upgrade_resumes_real_old_nested_interrupt_without_recreating_request(store, tmp_path, monkeypatch):
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import interrupt
    from parking.graph.schemas import AdminInput, AdminOutput, AdminState

    def old_admin_graph(model_factory, booking_store):
        def await_review(state):
            interrupt({"kind": "admin_approval", "reservation_id": state["reservation_id"],
                       "summary": state["reservation_summary"]})
            return {}
        old = StateGraph(AdminState, input_schema=AdminInput, output_schema=AdminOutput)
        old.add_node("await_review", await_review)
        old.add_edge(START, "await_review")
        old.add_edge("await_review", END)
        return old

    model = BookingModel()
    checkpoint = str(tmp_path / "upgrade.sqlite3")
    config = {"configurable": {"thread_id": "legacy-thread"}}
    with monkeypatch.context() as patch:
        patch.setattr("parking.graph.graph.build_admin_graph", old_admin_graph)
        async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
            old = build_graph(lambda: model, checkpointer=saver, booking_store=store)
            result = await old.ainvoke({"message": "Book my spot", "request_id": "legacy_request01"}, config)
            assert result["__interrupt__"] and model.calls["review"] == 0
            before = (await old.aget_state(config)).values
            reservation_id = before["reservation_id"]
            assert store.get(reservation_id)["status"] == "pending"
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        upgraded = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        result = await upgraded.ainvoke(Command(resume={"reservation_id": reservation_id}), config)
        assert "__interrupt__" not in result and "approved" in result["final_reply"]
        assert store.get(reservation_id)["status"] == "approved"
        assert model.calls["draft"] == model.calls["review"] == 1
        after = (await upgraded.aget_state(config)).values
        assert after["queries"] == before["queries"] and after["evidence"] == before["evidence"]
        assert "Private" not in json.dumps(result)
        await upgraded.ainvoke(None, config)
        assert model.calls["review"] == 1
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM booking_requests").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM reservations WHERE reservation_id=?", (reservation_id,)).fetchone()[0] == 1

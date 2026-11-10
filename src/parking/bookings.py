"""Pending slot holds alongside immutable legacy fixtures in the same SQLite file."""

from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from parking.api.sessions import Conflict, NotFound
from parking.graph.schemas import ReservationDraft


class BookingStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        # Never create an empty replacement for a missing fixture database.
        db = sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                db.execute("""CREATE TABLE IF NOT EXISTS booking_requests (
                    reservation_id TEXT PRIMARY KEY, thread_id TEXT NOT NULL,
                    request_id TEXT NOT NULL, spot_id TEXT NOT NULL, slot_date TEXT NOT NULL,
                    start_time TEXT NOT NULL, end_time TEXT NOT NULL,
                    draft TEXT NOT NULL, summary TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','confirmed','rejected')),
                    review_text TEXT, dispatch_status TEXT, review_run_id TEXT,
                    UNIQUE(thread_id, request_id),
                    FOREIGN KEY(spot_id, slot_date) REFERENCES transport_slots(spot_id, slot_date)
                )""")
            yield db
        finally:
            db.close()

    def reserve(self, thread_id, request_id, draft, summary):
        draft = ReservationDraft.model_validate(draft).model_dump()
        if any(not value or not value.strip() for value in draft.values()):
            raise ValueError("missing_details")
        try:
            start, end = (datetime.fromisoformat(draft[key]) for key in ("start", "end"))
            if start.utcoffset() is None or end.utcoffset() is None:
                raise ValueError()
            start, end = (value.astimezone(ZoneInfo("Europe/Warsaw")) for value in (start, end))
            if start.date() != end.date() or start >= end:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("invalid_interval") from None
        draft.update(start=start.isoformat(sep=" "), end=end.isoformat(sep=" "))
        payload = json.dumps(draft, sort_keys=True)
        reservation_id = str(uuid5(NAMESPACE_URL, f"parking:{thread_id}:{request_id}"))
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM booking_requests WHERE reservation_id=?", (reservation_id,)).fetchone()
            if existing:
                if existing["draft"] != payload:
                    raise Conflict()
                return dict(existing)
            slot = db.execute("SELECT working_hours FROM transport_slots WHERE spot_id=? AND slot_date=?",
                              (draft["spot_id"], start.date().isoformat())).fetchone()
            if not slot:
                raise ValueError("unknown_slot")
            opening, closing = slot["working_hours"].split("-")
            if start.strftime("%H:%M:%S") < opening + ":00" or end.strftime("%H:%M:%S") > closing + ":00":
                raise ValueError("outside_hours")
            # SQLite serializes writers before either overlap read. Pending requests hold slots.
            for table, statuses in (("reservations", "'confirmed','active','completed'"),
                                    ("booking_requests", "'pending','confirmed'")):
                overlap = db.execute(f"""SELECT 1 FROM {table} WHERE spot_id=?
                    AND status IN ({statuses}) AND julianday(start_time) < julianday(?)
                    AND julianday(end_time) > julianday(?) LIMIT 1""",
                    (draft["spot_id"], draft["end"], draft["start"])).fetchone()
                if overlap:
                    raise ValueError("slot_unavailable")
            db.execute("""INSERT INTO booking_requests
                (reservation_id,thread_id,request_id,spot_id,slot_date,start_time,end_time,draft,summary,status)
                VALUES (?,?,?,?,?,?,?,?,?,'pending')""",
                (reservation_id, thread_id, request_id, draft["spot_id"], start.date().isoformat(),
                 draft["start"], draft["end"], payload, summary))
            return dict(db.execute("SELECT * FROM booking_requests WHERE reservation_id=?", (reservation_id,)).fetchone())

    def get(self, reservation_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM booking_requests WHERE reservation_id=?", (reservation_id,)).fetchone()
        if not row:
            raise NotFound()
        return dict(row)

    def pending(self):
        with self.connection() as db:
            rows = db.execute("""SELECT reservation_id,thread_id,request_id,spot_id,start_time,end_time,
                summary,status,dispatch_status FROM booking_requests WHERE status='pending'
                ORDER BY rowid""").fetchall()
        return [dict(row) for row in rows]

    def decide(self, reservation_id, approved):
        target = "confirmed" if approved else "rejected"
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM booking_requests WHERE reservation_id=?", (reservation_id,)).fetchone()
            if not row:
                raise NotFound()
            if row["status"] not in ("pending", target):
                raise Conflict()
            db.execute("UPDATE booking_requests SET status=? WHERE reservation_id=?", (target, reservation_id))

    def claim_review(self, reservation_id, response):
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM booking_requests WHERE reservation_id=?", (reservation_id,)).fetchone()
            if not row:
                raise NotFound()
            if row["review_text"] is not None:
                if row["review_text"] != response:
                    raise Conflict()
                return False
            if row["status"] != "pending":
                raise Conflict()
            db.execute("UPDATE booking_requests SET review_text=?,dispatch_status='creating' WHERE reservation_id=?",
                       (response, reservation_id))
            return True

    def review_dispatched(self, reservation_id, run_id):
        with self.connection() as db, db:
            db.execute("UPDATE booking_requests SET dispatch_status='accepted',review_run_id=? WHERE reservation_id=?",
                       (run_id, reservation_id))

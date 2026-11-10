"""Pending slot holds alongside immutable legacy fixtures in the same SQLite file."""

from contextlib import contextmanager
from datetime import date, datetime
import json
from pathlib import Path
import re
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
                db.execute("BEGIN IMMEDIATE")
                db.execute("""CREATE TABLE IF NOT EXISTS booking_requests (
                    reservation_id TEXT PRIMARY KEY, thread_id TEXT NOT NULL,
                    request_id TEXT NOT NULL, spot_id TEXT NOT NULL, slot_date TEXT NOT NULL,
                    start_time TEXT NOT NULL, end_time TEXT NOT NULL,
                    draft TEXT NOT NULL, summary TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
                    review_text TEXT, dispatch_status TEXT, review_run_id TEXT,
                    decision_reason TEXT,
                    UNIQUE(thread_id, request_id),
                    FOREIGN KEY(spot_id, slot_date) REFERENCES transport_slots(spot_id, slot_date)
                )""")
                # Preserve all prior requests and dispatch claims while changing
                # only the application's status vocabulary, never legacy fixtures.
                schema = db.execute("SELECT sql FROM sqlite_master WHERE name='booking_requests'").fetchone()[0]
                if "'confirmed'" in schema:
                    db.execute(schema.replace("booking_requests", "booking_requests_migrated", 1)
                               .replace("'confirmed'", "'approved'"))
                    columns = [row[1] for row in db.execute("PRAGMA table_info(booking_requests)")]
                    projection = ["CASE WHEN status='confirmed' THEN 'approved' ELSE status END"
                                  if column == "status" else column for column in columns]
                    db.execute(f"INSERT INTO booking_requests_migrated ({','.join(columns)}) "
                               f"SELECT {','.join(projection)} FROM booking_requests")
                    db.execute("DROP TABLE booking_requests")
                    db.execute("ALTER TABLE booking_requests_migrated RENAME TO booking_requests")
                if "decision_reason" not in {row[1] for row in db.execute("PRAGMA table_info(booking_requests)")}:
                    db.execute("ALTER TABLE booking_requests ADD COLUMN decision_reason TEXT")
                self._migrate_reservations_date_range(db)
            yield db
        finally:
            db.close()

    @staticmethod
    def _migrate_reservations_date_range(db):
        """Remove the fixture-only date bound while preserving every reservation row."""
        row = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reservations'").fetchone()
        if not row or not re.search(r"slot_date\s+BETWEEN\s+'2026-11-01'\s+AND\s+'2026-11-10'", row[0], re.I):
            return

        schema = row[0]
        migrated_schema = re.sub(
            r"\s*CHECK\s*\(\s*slot_date\s+BETWEEN\s+'2026-11-01'\s+AND\s+'2026-11-10'\s*\)",
            "",
            schema,
            count=1,
            flags=re.I,
        )
        migrated_schema = re.sub(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?reservations\b",
            "CREATE TABLE reservations_migrated",
            migrated_schema,
            count=1,
            flags=re.I,
        )
        columns = [column[1] for column in db.execute("PRAGMA table_info(reservations)")]
        names = ",".join(f'"{column}"' for column in columns)
        db.execute(migrated_schema)
        db.execute(f"INSERT INTO reservations_migrated ({names}) SELECT {names} FROM reservations")
        db.execute("DROP TABLE reservations")
        db.execute("ALTER TABLE reservations_migrated RENAME TO reservations")
        db.execute("CREATE INDEX IF NOT EXISTS reservations_spot_time ON reservations (spot_id, start_time, end_time)")

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
            self.validate_slot(db, draft, reservation_id)
            db.execute("""INSERT INTO booking_requests
                (reservation_id,thread_id,request_id,spot_id,slot_date,start_time,end_time,draft,summary,status)
                VALUES (?,?,?,?,?,?,?,?,?,'pending')""",
                (reservation_id, thread_id, request_id, draft["spot_id"], start.date().isoformat(),
                 draft["start"], draft["end"], payload, summary))
            return dict(db.execute("SELECT * FROM booking_requests WHERE reservation_id=?", (reservation_id,)).fetchone())

    def find_slots(self, facility, *, slot_date=None, start=None, end=None,
                   duration_hours=None, spot_id=None, spot_type=None, limit=3):
        """Return only public, facility-scoped candidates; times enable availability checks."""
        facility = facility.upper() if isinstance(facility, str) else ""
        if facility not in ("CTR", "RIV", "STA", "AIR"):
            raise ValueError("Choose a parking location")
        if not 1 <= limit <= 12:
            raise ValueError("Invalid result limit")
        if slot_date is not None:
            slot_date = date.fromisoformat(slot_date).isoformat()
        interval = bool(start and end)
        if not interval and (start or end):
            partial = ReservationDraft(start=start, end=end)
            given_date = (partial.start or partial.end)[:10]
            if slot_date and slot_date != given_date:
                raise ValueError("Date does not match interval")
            slot_date = given_date
        if interval:
            times = ReservationDraft(start=start, end=end)
            start, end = (datetime.fromisoformat(value) for value in (times.start, times.end))
            if start.date() != end.date() or start >= end:
                raise ValueError("invalid_interval")
            if slot_date and slot_date != start.date().isoformat():
                raise ValueError("Date does not match interval")
            slot_date = start.date().isoformat()
            duration_hours = (end - start).total_seconds() / 3600
        if duration_hours is not None and not 0 < duration_hours <= 24:
            raise ValueError("Invalid duration")
        # SQLite has no ILIKE. COLLATE NOCASE + LIKE with bound, validated
        # prefixes is its equivalent here; no caller can supply SQL/wildcards.
        filters = ["s.spot_id COLLATE NOCASE LIKE ?"]
        values = [facility + "-%"]
        if spot_type is not None:
            if spot_type not in ("standard", "electric", "accessible", "van"):
                raise ValueError("Invalid space type")
            filters.append("s.type = ?")
            values.append(spot_type)
        if slot_date:
            filters.append("s.slot_date = ?")
            values.append(slot_date)
        if spot_id:
            filters.append("s.spot_id = ? COLLATE NOCASE")
            values.append(spot_id)
        if interval:
            filters.extend([
                "? >= substr(s.working_hours,1,5) || ':00'",
                "? <= substr(s.working_hours,7,5) || ':00'",
                """NOT EXISTS (SELECT 1 FROM reservations r WHERE r.spot_id=s.spot_id
                    AND r.status IN ('confirmed','active','completed')
                    AND julianday(r.start_time) < julianday(?)
                    AND julianday(r.end_time) > julianday(?))""",
                """NOT EXISTS (SELECT 1 FROM booking_requests b WHERE b.spot_id=s.spot_id
                    AND b.status IN ('pending','approved')
                    AND julianday(b.start_time) < julianday(?)
                    AND julianday(b.end_time) > julianday(?))""",
            ])
            values.extend([start.strftime("%H:%M:%S"), end.strftime("%H:%M:%S"),
                           end.isoformat(), start.isoformat(), end.isoformat(), start.isoformat()])
        with self.connection() as db:
            rows = db.execute(f"""SELECT DISTINCT s.spot_id, s.type, s.hourly_price, s.working_hours
                FROM transport_slots s WHERE {' AND '.join(filters)}
                ORDER BY s.hourly_price, s.spot_id LIMIT ?""", [*values, limit]).fetchall()
        return [{**dict(row), "slot_date": slot_date, "availability_checked": interval,
                 "total_price": round(row["hourly_price"] * duration_hours, 2) if duration_hours else None,
                 "currency": "PLN"} for row in rows]

    def validate_slot(self, db, draft, reservation_id):
        """Check hours and conflicts under the caller's SQLite write transaction."""
        start, end = (datetime.fromisoformat(draft[key]) for key in ("start", "end"))
        slot = db.execute("SELECT working_hours FROM transport_slots WHERE spot_id=? AND slot_date=?",
                          (draft["spot_id"], start.date().isoformat())).fetchone()
        if not slot:
            raise ValueError("unknown_slot")
        opening, closing = slot["working_hours"].split("-")
        if start.strftime("%H:%M:%S") < opening + ":00" or end.strftime("%H:%M:%S") > closing + ":00":
            raise ValueError("outside_hours")
        for table, statuses in (("reservations", "'confirmed','active','completed'"),
                                ("booking_requests", "'pending','approved'")):
            exclusion = " AND reservation_id != ?" if table == "booking_requests" else ""
            values = [draft["spot_id"], draft["end"], draft["start"]]
            if exclusion:
                values.append(reservation_id)
            overlap = db.execute(f"""SELECT 1 FROM {table} WHERE spot_id=?
                AND status IN ({statuses}) AND julianday(start_time) < julianday(?)
                AND julianday(end_time) > julianday(?){exclusion} LIMIT 1""", values).fetchone()
            if overlap:
                raise ValueError("slot_unavailable")

    def set_summary(self, reservation_id, summary):
        with self.connection() as db, db:
            db.execute("UPDATE booking_requests SET summary=? WHERE reservation_id=? AND status='pending'",
                       (summary, reservation_id))

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
        target = "approved" if approved else "rejected"
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM booking_requests WHERE reservation_id=?", (reservation_id,)).fetchone()
            if not row:
                raise NotFound()
            # A failed approval remains a rejection on tool/checkpoint replay.
            if row["status"] == target or (approved and row["status"] == "rejected" and row["decision_reason"]):
                return dict(row)
            if row["status"] != "pending":
                raise Conflict()
            reason = None
            if approved:
                try:
                    draft = ReservationDraft.model_validate(json.loads(row["draft"])).model_dump()
                    if any(not value or not value.strip() for value in draft.values()):
                        raise ValueError("missing_details")
                    self.validate_slot(db, draft, reservation_id)
                except ValueError as error:
                    target, reason = "rejected", str(error)
            if approved and target == "approved":
                start = datetime.fromisoformat(draft["start"])
                created_at = datetime.now(ZoneInfo("Europe/Warsaw")).isoformat(sep=" ")
                db.execute("""INSERT INTO reservations
                    (reservation_id,spot_id,slot_date,name,surname,car_number,start_time,end_time,status,created_at)
                    VALUES (?,?,?,?,?,?,?,?, 'confirmed',?)""",
                    (reservation_id, draft["spot_id"], start.date().isoformat(), draft["name"],
                     draft["surname"], draft["car_number"], draft["start"].replace("T", " "),
                     draft["end"].replace("T", " "), created_at))
            # The pending row must already exist. Updating by its primary key is
            # the conflict-update part of the upsert, without an insert fallback
            # that could create an unvalidated reservation or overwrite its data.
            db.execute("UPDATE booking_requests SET status=?,decision_reason=? WHERE reservation_id=?",
                       (target, reason, reservation_id))
            return dict(db.execute("SELECT * FROM booking_requests WHERE reservation_id=?", (reservation_id,)).fetchone())

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

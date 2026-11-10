"""Scoped public SQL search over realistic daily slots and blocking reservations."""

import sqlite3

import pytest

from parking.bookings import BookingStore


@pytest.fixture
def slot_store(tmp_path):
    path = tmp_path / "slots.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE transport_slots (spot_id TEXT, slot_date TEXT, type TEXT,
                hourly_price REAL, working_hours TEXT, current_availability INTEGER,
                PRIMARY KEY (spot_id,slot_date));
            CREATE TABLE reservations (spot_id TEXT, start_time TEXT, end_time TEXT,
                status TEXT, name TEXT, car_number TEXT);
        """)
        for day in ("2026-11-20", "2026-11-21"):
            for prefix, price in (("CTR", 8), ("AIR", 5), ("RIV", 6), ("STA", 7)):
                db.executemany("INSERT INTO transport_slots VALUES (?,?,?,?,?,0)",
                    [(f"{prefix}-{number:03}", day, "standard", price, "06:00-22:00") for number in range(1, 5)])
        db.execute("INSERT INTO transport_slots VALUES ('AIR-999','2026-11-22','van',7,'06:00-22:00',1)")
    return BookingStore(path)


@pytest.mark.parametrize("facility,price", [("ctr", 8), ("AIR", 5), ("RIV", 6), ("STA", 7)])
def test_prefix_date_price_and_public_projection(slot_store, facility, price):
    rows = slot_store.find_slots(facility, slot_date="2026-11-20", duration_hours=6)
    assert len(rows) == 3
    assert all(row["spot_id"].startswith(facility.upper() + "-") for row in rows)
    assert all(row["slot_date"] == "2026-11-20" for row in rows)
    assert all(row["hourly_price"] == price and row["total_price"] == price * 6 for row in rows)
    assert all(not row["availability_checked"] for row in rows)
    assert set(rows[0]) == {"spot_id", "type", "hourly_price", "working_hours", "slot_date",
                            "availability_checked", "total_price", "currency"}
    assert not slot_store.find_slots(facility, slot_date="2026-12-01")


def test_date_filter_does_not_include_later_days_and_no_date_deduplicates(slot_store):
    assert not slot_store.find_slots("AIR", slot_date="2026-11-20", spot_id="AIR-999")
    rows = slot_store.find_slots("AIR", limit=12)
    assert len(rows) == 5 and all(row["slot_date"] is None for row in rows)
    assert not slot_store.find_slots("CTR", spot_id="AIR-001")


@pytest.mark.parametrize("facility", ["", "%", "CTR%' OR 1=1 --", "CITY", "AIR_%"])
def test_invalid_prefix_cannot_broaden_query(slot_store, facility):
    with pytest.raises(ValueError):
        slot_store.find_slots(facility)


def test_overlap_pending_approved_hours_and_snapshot_semantics(slot_store):
    start, end = "2026-11-20T16:00:00+01:00", "2026-11-20T22:00:00+01:00"
    with sqlite3.connect(slot_store.path) as db:
        db.execute("INSERT INTO reservations VALUES (?,?,?,'confirmed','PRIVATE','SECRET')",
                   ("CTR-001", start, "2026-11-20T18:00:00+01:00"))
        db.execute("INSERT INTO reservations VALUES (?,?,?,'cancelled','PRIVATE','SECRET')", ("CTR-004", start, end))
    draft = {"spot_id": "CTR-002", "start": start, "end": end,
             "name": "Private", "surname": "Person", "car_number": "SECRET"}
    held = slot_store.reserve("thread", "hold", draft, "")
    rows = slot_store.find_slots("CTR", start=start, end=end)
    assert [row["spot_id"] for row in rows] == ["CTR-003", "CTR-004"]
    assert rows[0]["total_price"] == 48 and rows[0]["availability_checked"]
    assert "PRIVATE" not in str(rows) and "SECRET" not in str(rows)
    slot_store.decide(held["reservation_id"], True)
    assert slot_store.find_slots("CTR", start=start, end=end) == rows
    assert not slot_store.find_slots("CTR", start=start, end="2026-11-20T23:00:00+01:00")
    # Adjacent intervals do not overlap; current_availability=0 is only a seed snapshot.
    assert slot_store.find_slots("CTR", start="2026-11-20T18:00:00+01:00", end=end, spot_id="CTR-001")

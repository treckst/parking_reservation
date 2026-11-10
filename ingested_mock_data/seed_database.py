"""Run once: python ingested_mock_data/seed_database.py (standard library only).

Fictional PLN prices and Europe/Warsaw local timestamps (UTC+01:00 in November).
Availability/status snapshot: 2026-11-09 12:00:00+01:00. Reruns preserve existing rows.
"""

import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


random.seed(202611)
database = Path(__file__).with_name("parking_november_2026.sqlite3")
local_timezone = timezone(timedelta(hours=1))
snapshot = datetime(2026, 11, 9, 12, tzinfo=local_timezone)
names = [
    ("Anna", "Kowalska"), ("Jan", "Nowak"), ("Maria", "Wisniewska"),
    ("Piotr", "Wojcik"), ("Ewa", "Kaminska"), ("Adam", "Lewandowski"),
    ("Julia", "Zielinska"), ("Michal", "Szymanski"), ("Zofia", "Dabrowska"),
    ("Tomasz", "Kozlowski"), ("Olena", "Melnyk"), ("Daniel", "Novak"),
]
# Prefix identifies the facility described in the accompanying PDFs.
facilities = [("CTR", 8.0), ("RIV", 6.0), ("STA", 7.0), ("AIR", 5.0)]
spots = []
for prefix, base_price in facilities:
    for number in range(1, 13):
        spot_type = (
            "standard" if number <= 6 else "electric" if number <= 8
            else "accessible" if number <= 10 else "van"
        )
        price = base_price + (2 if spot_type in ("electric", "van") else 0)
        spots.append((f"{prefix}-{number:03d}", spot_type, price))

reservations = []
occupied_now = set()
for day in range(1, 11):
    # Three non-overlapping visits per selected spot; unused spots remain bookable.
    for spot_id, _, _ in random.sample(spots, 24):
        for hour in (7, 11, 16):
            start = datetime(2026, 11, day, hour, tzinfo=local_timezone)
            end = start + timedelta(hours=random.choice((2, 3, 4)))
            created = start - timedelta(hours=random.randint(2, 72))
            cancelled = random.random() < 0.12
            status = (
                "cancelled" if cancelled else "completed" if end <= snapshot
                else "active" if start <= snapshot < end else "confirmed"
            )
            if status == "active":
                occupied_now.add(spot_id)
            name, surname = random.choice(names)
            reservation_id = f"RES-202611{day:02d}-{spot_id}-{hour:02d}"
            reservations.append((
                reservation_id, spot_id, start.date().isoformat(), name, surname,
                f"WX {random.randint(10000, 99999)}",
                start.isoformat(sep=" "), end.isoformat(sep=" "), status,
                created.isoformat(sep=" "),
            ))

daily_slots = []
for day in range(1, 31):
    slot_date = f"2026-11-{day:02d}"
    for spot_id, spot_type, price in spots:
        # Past dates cannot be booked; today's occupied spots are unavailable now.
        # A future date marked available can still contain reserved time intervals.
        available = day >= 9 and not (day == 9 and spot_id in occupied_now)
        daily_slots.append((spot_id, slot_date, spot_type, price, "06:00-22:00", int(available)))

connection = sqlite3.connect(database)
try:
    connection.execute("PRAGMA foreign_keys = ON")
    with connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS transport_slots (
                spot_id TEXT NOT NULL,
                slot_date TEXT NOT NULL CHECK (slot_date BETWEEN '2026-11-01' AND '2026-11-30'),
                type TEXT NOT NULL CHECK (type IN ('standard', 'electric', 'accessible', 'van')),
                hourly_price REAL NOT NULL CHECK (hourly_price > 0),
                working_hours TEXT NOT NULL,
                current_availability INTEGER NOT NULL CHECK (current_availability IN (0, 1)),
                PRIMARY KEY (spot_id, slot_date)
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id TEXT PRIMARY KEY NOT NULL,
                spot_id TEXT NOT NULL,
                slot_date TEXT NOT NULL CHECK (slot_date BETWEEN '2026-11-01' AND '2026-11-10'),
                name TEXT NOT NULL,
                surname TEXT NOT NULL,
                car_number TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL CHECK (end_time > start_time),
                status TEXT NOT NULL CHECK (status IN ('confirmed', 'active', 'completed', 'cancelled')),
                created_at TEXT NOT NULL CHECK (created_at <= start_time),
                CHECK (substr(start_time, 1, 10) = slot_date),
                CHECK (substr(end_time, 1, 10) = slot_date),
                FOREIGN KEY (spot_id, slot_date) REFERENCES transport_slots (spot_id, slot_date)
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS reservations_spot_time
            ON reservations (spot_id, start_time, end_time)
        """)
        connection.executemany("""
            INSERT INTO transport_slots
                (spot_id, slot_date, type, hourly_price, working_hours, current_availability)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (spot_id, slot_date) DO NOTHING
        """, daily_slots)
        connection.executemany("""
            INSERT INTO reservations
                (reservation_id, spot_id, slot_date, name, surname, car_number,
                 start_time, end_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (reservation_id) DO NOTHING
        """, reservations)
    print(f"Database: {database}")
    for table in ("transport_slots", "reservations"):
        print(f"{table}: {connection.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]} rows")
finally:
    connection.close()

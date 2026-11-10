"""Short SQLite transactions for server-issued owners and thread bindings."""

from contextlib import contextmanager
import secrets
import sqlite3
import time


class Conflict(Exception):
    pass


class NotFound(Exception):
    pass


class Registry:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS owners (
                    owner TEXT PRIMARY KEY, created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS threads (
                    thread_id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES owners(owner),
                    created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS submissions (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner TEXT NOT NULL, thread_id TEXT NOT NULL REFERENCES threads(thread_id),
                    request_id TEXT NOT NULL, message TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN (
                        'reserved','creating','acceptance_unknown','accepted','completed','proven_failed'
                    )), run_id TEXT, result TEXT, created REAL NOT NULL,
                    UNIQUE(thread_id, request_id)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_per_thread
                ON submissions(thread_id)
                WHERE status IN ('reserved','creating','acceptance_unknown','accepted');
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def owner(self, token):
        with self.connection() as db:
            if token and db.execute("SELECT 1 FROM owners WHERE owner=?", (token,)).fetchone():
                return token
            token = secrets.token_urlsafe(32)
            db.execute("INSERT INTO owners VALUES (?, ?)", (token, time.time()))
        return token

    def bind_thread(self, owner, thread_id):
        with self.connection() as db:
            db.execute("INSERT INTO threads VALUES (?, ?, ?)", (thread_id, owner, time.time()))

    def require_thread(self, owner, thread_id):
        with self.connection() as db:
            found = db.execute(
                "SELECT 1 FROM threads WHERE owner=? AND thread_id=?", (owner, thread_id)
            ).fetchone()
        if not found:
            raise NotFound()

    def conversation(self, owner, thread_id):
        self.require_thread(owner, thread_id)
        with self.connection() as db:
            rows = db.execute(
                "SELECT request_id,message,status,result FROM submissions WHERE owner=? AND thread_id=? ORDER BY sequence",
                (owner, thread_id),
            ).fetchall()
        return [dict(row) for row in rows]

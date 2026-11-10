"""Durable submission identity, contention and conditional crash recovery."""

import hashlib
import json
import sqlite3
import time

from parking.api.sessions import Conflict, NotFound


class Submissions:
    def __init__(self, registry):
        self.registry = registry

    def get(self, owner, thread_id, request_id):
        self.registry.require_thread(owner, thread_id)
        with self.registry.connection() as db:
            row = db.execute(
                "SELECT * FROM submissions WHERE owner=? AND thread_id=? AND request_id=?",
                (owner, thread_id, request_id),
            ).fetchone()
        if not row:
            raise NotFound()
        return dict(row)

    def reserve(self, owner, thread_id, request_id, message):
        self.registry.require_thread(owner, thread_id)
        fingerprint = hashlib.sha256(message.encode("utf-8")).hexdigest()
        try:
            with self.registry.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT * FROM submissions WHERE thread_id=? AND request_id=?", (thread_id, request_id)
                ).fetchone()
                if row:
                    if row["owner"] != owner or row["fingerprint"] != fingerprint:
                        raise Conflict()
                    if row["status"] == "proven_failed":
                        db.execute(
                            "UPDATE submissions SET status='reserved',run_id=NULL,result=NULL WHERE sequence=?",
                            (row["sequence"],),
                        )
                else:
                    db.execute(
                        "INSERT INTO submissions(owner,thread_id,request_id,message,fingerprint,status,created) VALUES (?,?,?,?,?,'reserved',?)",
                        (owner, thread_id, request_id, message, fingerprint, time.time()),
                    )
        except sqlite3.IntegrityError as error:
            raise Conflict() from error
        return self.get(owner, thread_id, request_id)

    def transition(self, row, expected, status, *, run_id=None, result=None):
        with self.registry.connection() as db:
            cursor = db.execute(
                "UPDATE submissions SET status=?,run_id=COALESCE(?,run_id),result=COALESCE(?,result) "
                "WHERE sequence=? AND status=?",
                (status, run_id, json.dumps(result) if result is not None else None, row["sequence"], expected),
            )
            return cursor.rowcount == 1

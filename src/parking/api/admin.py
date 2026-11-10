"""Trusted local admin API adapter; uncertain resume acceptance never creates twice."""

import asyncio

from parking.api.sessions import Conflict


class AdminGateway:
    def __init__(self, client, store, submissions):
        self.client, self.store, self.submissions = client, store, submissions

    async def reconcile(self, row):
        if row["dispatch_status"] == "creating":
            for offset in range(0, 10000, 100):
                runs = await asyncio.wait_for(self.client.runs.list(row["thread_id"], limit=100, offset=offset), 20)
                matches = [run for run in runs if run.get("metadata", {}).get("admin_review_id") == row["reservation_id"]]
                if matches:
                    if len(matches) != 1:
                        raise Conflict()
                    self.store.review_dispatched(row["reservation_id"], matches[0]["run_id"])
                    break
                if len(runs) < 100:
                    break
            row = self.store.get(row["reservation_id"])
        if row["review_run_id"]:
            # Reconnect customer polling to the continuation, including after API restart.
            with self.submissions.registry.connection() as db, db:
                db.execute("""UPDATE submissions SET run_id=? WHERE thread_id=? AND request_id=?
                    AND status='accepted'""", (row["review_run_id"], row["thread_id"], row["request_id"]))
        return row

    async def review(self, reservation_id, response):
        row = self.store.get(reservation_id)
        if row["review_text"] is None:
            state = await asyncio.wait_for(self.client.threads.get_state(row["thread_id"]), 20)
            values = state.get("values", {})
            if (values.get("reservation_id") != reservation_id
                    or values.get("request_id") != row["request_id"] or "admin" not in state.get("next", [])):
                raise Conflict()
        claimed = self.store.claim_review(reservation_id, response)
        if claimed:
            # A crash/lost acknowledgement leaves 'creating'. Reconcile; never blindly retry.
            run = await asyncio.wait_for(self.client.runs.create(
                row["thread_id"], "parking",
                command={"resume": {"reservation_id": reservation_id, "response": response}},
                metadata={"admin_review_id": reservation_id},
                multitask_strategy="reject", durability="sync",
            ), 20)
            self.store.review_dispatched(reservation_id, run["run_id"])
        row = await self.reconcile(self.store.get(reservation_id))
        return {"reservation_id": reservation_id, "status": row["status"],
                "dispatch_status": row["dispatch_status"]}

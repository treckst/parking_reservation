"""Remote SDK only; uncertain acceptance never triggers another run creation."""

import asyncio
import json

from langgraph_sdk import get_client

from parking.graph.schemas import GraphOutput


class Gateway:
    def __init__(self, settings, submissions, client=None):
        self.client = client or get_client(url=settings.graph_url, timeout=20)
        self.submissions = submissions

    async def create_thread(self):
        thread = await asyncio.wait_for(self.client.threads.create(), timeout=20)
        return thread["thread_id"]

    async def submit(self, owner, thread_id, request_id, message):
        row = self.submissions.reserve(owner, thread_id, request_id, message)
        if row["status"] == "reserved" and self.submissions.transition(row, "reserved", "creating"):
            try:
                run = await asyncio.wait_for(self.client.runs.create(
                    thread_id, "parking", input={"message": message, "request_id": request_id},
                    metadata={"request_id": request_id, "payload_fingerprint": row["fingerprint"]},
                    multitask_strategy="reject", durability="sync",
                ), timeout=20)
            except BaseException:
                self.submissions.transition(row, "creating", "acceptance_unknown")
                # Even cancellation may follow remote acceptance. Status can reconcile it.
                raise
            self.submissions.transition(row, "creating", "accepted", run_id=run["run_id"])
        return await self.status(owner, thread_id, request_id)

    async def reconcile(self, row):
        matches = {}
        # Bound work; when the bound is reached retain uncertainty, never recreate.
        for offset in range(0, 10000, 100):
            runs = await asyncio.wait_for(
                self.client.runs.list(row["thread_id"], limit=100, offset=offset), timeout=20
            )
            for run in runs:
                metadata = run.get("metadata", {})
                if metadata.get("request_id") == row["request_id"] and metadata.get("payload_fingerprint") == row["fingerprint"]:
                    matches[run["run_id"]] = run
            if len(runs) < 100:
                if len(matches) == 1:
                    run = next(iter(matches.values()))
                    self.submissions.transition(row, row["status"], "accepted", run_id=run["run_id"])
                return

    async def status(self, owner, thread_id, request_id):
        row = self.submissions.get(owner, thread_id, request_id)
        if row["status"] in ("creating", "acceptance_unknown"):
            await self.reconcile(row)
            row = self.submissions.get(owner, thread_id, request_id)
        if row["status"] == "accepted":
            run = await asyncio.wait_for(self.client.runs.get(thread_id, row["run_id"]), timeout=20)
            if run["status"] == "success":
                # Read only after confirmed completion; never forward the raw state.
                await asyncio.wait_for(self.client.runs.join(thread_id, row["run_id"]), timeout=20)
                state = await asyncio.wait_for(self.client.threads.get_state(thread_id), timeout=20)
                values = state.get("values", {})
                output = GraphOutput.model_validate({key: values.get(key) for key in GraphOutput.model_fields})
                if output.request_id != request_id:
                    raise ValueError("Mismatched final response")
                self.submissions.transition(row, "accepted", "completed", result=output.model_dump())
            elif run["status"] in ("error", "timeout", "interrupted"):
                self.submissions.transition(row, "accepted", "proven_failed")
            row = self.submissions.get(owner, thread_id, request_id)
        return self.project(row)

    @staticmethod
    def project(row):
        status = row["status"]
        return {
            "thread_id": row["thread_id"], "request_id": row["request_id"],
            "status": "completed" if status == "completed" else "failed" if status == "proven_failed" else "pending",
            "reply": json.loads(row["result"]) if status == "completed" else None,
            "error_code": "request_failed" if status == "proven_failed" else None,
            "retryable": status == "proven_failed",
        }

"""Expose exact synchronous SqliteSaver storage through the server's async API."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import partial
import sqlite3

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver

from parking.settings import Settings


class ServerSqliteAdapter(BaseCheckpointSaver[str]):
    """Serialize SQLite work on one worker; cancellation never closes a busy DB."""

    def __init__(self, saver: SqliteSaver):
        super().__init__(serde=saver.serde)
        self.saver = saver
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="checkpoint")
        self._closed = False

    async def _call(self, function, *args, **kwargs):
        if self._closed:
            raise RuntimeError("Checkpoint adapter is closed")
        future = asyncio.get_running_loop().run_in_executor(
            self._worker, partial(function, *args, **kwargs)
        )
        # Cancelling an awaiting request must not cancel a queued database write.
        return await asyncio.shield(future)

    async def aget_tuple(self, config):
        return await self._call(self.saver.get_tuple, config)

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await self._call(self.saver.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        await self._call(self.saver.put_writes, config, writes, task_id, task_path)

    async def alist(self, config, *, filter=None, before=None, limit=None):
        def read_history():
            return list(self.saver.list(config, filter=filter, before=before, limit=limit))

        for checkpoint in await self._call(read_history):
            yield checkpoint

    async def adelete_thread(self, thread_id):
        await self._call(self.saver.delete_thread, thread_id)

    def get_next_version(self, current, channel):
        return self.saver.get_next_version(current, channel)

    async def aclose(self):
        if not self._closed:
            self._closed = True
            await asyncio.to_thread(self._worker.shutdown, wait=True)


@asynccontextmanager
async def generate_checkpointer(path=None):
    settings = Settings.from_env(checkpoint_path=path)
    path = settings.checkpoint_path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    adapter = ServerSqliteAdapter(SqliteSaver(connection))
    try:
        yield adapter
    finally:
        # Shield shutdown too: the connection outlives queued/cancelled requests.
        async def close():
            await adapter.aclose()
            connection.close()

        closing = asyncio.create_task(close())
        try:
            await asyncio.shield(closing)
        except asyncio.CancelledError:
            await closing
            raise

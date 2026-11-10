"""Own the SQLite connection outside graph construction."""

from contextlib import asynccontextmanager
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver


@asynccontextmanager
async def generate_checkpointer(path):
    connection = sqlite3.connect(path, check_same_thread=False)
    try:
        yield SqliteSaver(connection)
    finally:
        connection.close()

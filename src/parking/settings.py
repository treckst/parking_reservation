"""Small environment configuration, with separate application storage files."""

from dataclasses import dataclass
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOKING_DB = ROOT / "ingested_mock_data/parking_november_2026.sqlite3"


@dataclass(frozen=True)
class Settings:
    checkpoint_path: Path
    application_path: Path
    booking_path: Path = BOOKING_DB
    chroma_host: str = "127.0.0.1"
    chroma_port: int = 8000
    graph_url: str = "http://127.0.0.1:8123"
    allowed_origins: tuple[str, ...] = ("http://127.0.0.1:8080", "http://localhost:8080")

    def __post_init__(self):
        paths = [self.checkpoint_path.resolve(), self.application_path.resolve(), self.booking_path.resolve()]
        if len(set(paths)) != 3:
            raise ValueError("Checkpoint, application registry, and booking databases must be separate files")
        for left, right in [(paths[0], paths[1]), (paths[0], paths[2]), (paths[1], paths[2])]:
            if left.exists() and right.exists() and left.samefile(right):
                raise ValueError("Database paths must not refer to the same file")
        if not self.chroma_host or not 1 <= self.chroma_port <= 65535:
            raise ValueError("Invalid Chroma address")

    @classmethod
    def from_env(cls, *, checkpoint_path=None):
        return cls(
            checkpoint_path=Path(checkpoint_path or os.getenv("CHECKPOINT_DB_PATH", ROOT / ".runtime/checkpoints.sqlite3")),
            application_path=Path(os.getenv("APPLICATION_DB_PATH", ROOT / ".runtime/application.sqlite3")),
            booking_path=Path(os.getenv("BOOKING_DB_PATH", BOOKING_DB)),
            chroma_host=os.getenv("CHROMA_HOST", "127.0.0.1"),
            chroma_port=int(os.getenv("CHROMA_PORT", "8000")),
            graph_url=os.getenv("GRAPH_URL", "http://127.0.0.1:8123"),
            allowed_origins=tuple(os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8080,http://localhost:8080").split(",")),
        )

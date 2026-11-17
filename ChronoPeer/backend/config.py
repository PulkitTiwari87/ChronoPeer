"""Runtime settings, read from environment variables (see .env.example)."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the ChronoPeer/ folder


@dataclass(frozen=True)
class Settings:
    db_path: Path
    storage_dir: Path
    reports_dir: Path
    max_upload_bytes: int = 5 * 1024 * 1024
    seed_demo: bool = False
    frontend_dir: Path = ROOT / "frontend" / "dist"
    ephemeral: bool = False  # True when storage is temporary (free hosting); the UI says so


def _path(env_name: str, default: str) -> Path:
    p = Path(os.environ.get(env_name, default))
    return p if p.is_absolute() else ROOT / p


def load_settings() -> Settings:
    return Settings(
        db_path=_path("CHRONOPEER_DB", "instance/chronopeer.db"),
        storage_dir=_path("CHRONOPEER_STORAGE", "backend/storage"),
        reports_dir=_path("CHRONOPEER_REPORTS", "reports"),
        max_upload_bytes=int(os.environ.get("CHRONOPEER_MAX_UPLOAD_BYTES", 5 * 1024 * 1024)),
        seed_demo=os.environ.get("CHRONOPEER_SEED_DEMO", "1") == "1",
        ephemeral=os.environ.get("CHRONOPEER_EPHEMERAL", "0") == "1",
    )

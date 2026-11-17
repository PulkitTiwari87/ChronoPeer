"""Vercel entry point: the same FastAPI app, on temporary storage, with the demo case seeded.

Vercel serves the built React app as static files and sends /api/* here (see vercel.json).
A function's disk is per-instance and temporary, so the database is rebuilt on every cold start.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import Settings  # noqa: E402
from backend.main import create_app  # noqa: E402

_tmp = Path(tempfile.gettempdir()) / "chronopeer"
app = create_app(
    Settings(
        db_path=_tmp / "chronopeer.db",
        storage_dir=_tmp / "storage",
        reports_dir=_tmp / "reports",
        seed_demo=True,
        ephemeral=True,
        frontend_dir=_tmp / "no-frontend",  # the UI is served by Vercel, not by this function
    )
)

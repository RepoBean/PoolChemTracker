"""Runtime configuration from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

# Default DB lives in the repo/container's ./data (bind-mounted in prod).
_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "poolmath.db"

DB_PATH = os.getenv("POOLMATH_DB_PATH", str(_DEFAULT_DB))
AUTH_TOKEN = os.getenv("POOLMATH_AUTH_TOKEN") or None  # unset -> open on LAN
TZ = os.getenv("TZ", "UTC")

# Optional local vision model for receipt scanning (Ollama /api/chat).
# Unset VLM_URL = feature off: endpoints 503, frontend hides the button.
VLM_URL = os.getenv("POOLMATH_VLM_URL") or None
VLM_MODEL = os.getenv("POOLMATH_VLM_MODEL", "llama3.2-vision")

# Built frontend to serve (repo layout in dev; overridden in the Docker image).
STATIC_DIR = os.getenv(
    "POOLMATH_STATIC_DIR",
    str(Path(__file__).resolve().parents[2] / "frontend" / "dist"),
)


def database_url() -> str:
    """SQLite URL. `POOLMATH_DATABASE_URL` overrides (used by tests)."""
    override = os.getenv("POOLMATH_DATABASE_URL")
    if override:
        return override
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH}"

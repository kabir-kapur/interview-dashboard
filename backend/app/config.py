"""Small runtime configuration shared by the API routes."""

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/interview_console.db"


def cors_origins() -> list[str]:
    """Read the browser origins permitted to call this API."""
    configured = os.getenv("CORS_ORIGINS")
    return [origin.strip() for origin in configured.split(",") if origin.strip()] if configured else ["http://localhost:3000"]

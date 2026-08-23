"""Vercel ASGI entry point for the Uzbekistan OS FastAPI service."""

import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.main import app  # noqa: E402

__all__ = ["app"]

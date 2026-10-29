"""Vercel entry point: runs the FastAPI app as a serverless function.

Vercel serves the built frontend itself, so only the API runs here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import create_app  # noqa: E402

app = create_app()

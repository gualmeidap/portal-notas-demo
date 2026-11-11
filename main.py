"""Compatibility entry point: `uvicorn main:app` keeps working for hosts
configured before the code moved to the `app/` package."""
from app.main import app  # noqa: F401

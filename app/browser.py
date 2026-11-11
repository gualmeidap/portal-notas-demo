"""Browser runtime (GitHub Pages).

Pyodide runs this module inside the visitor's browser. `web/static/runtime.js`
routes the page's API calls to `handle()`, so the UI, the route table and the
business logic are exactly the ones the server uses. There is one visitor per
browser tab, so there is one sandbox.
"""
from __future__ import annotations

import json
from typing import Optional

from . import api
from .i18n import pick_lang
from .sandbox import Sandbox

_sandbox: Optional[Sandbox] = None


def boot() -> None:
    global _sandbox
    _sandbox = Sandbox()


def handle(method: str, path: str, query_json: str, body_json: Optional[str], form_json: Optional[str],
           files: Optional[list], lang: str):
    """Returns (status, kind, payload, media_type, filename, inline).

    kind is "json" (payload: JSON text) or "file" (payload: bytes)."""
    global _sandbox
    if _sandbox is None:
        boot()
    if path == "/api/reset" and method == "POST":
        boot()
        return 200, "json", json.dumps({"success": True}), "", "", True
    req = api.Request(method=method, path=path, query=json.loads(query_json or "{}"),
                      json=json.loads(body_json) if body_json else None,
                      form=json.loads(form_json) if form_json else None,
                      files=[(name, bytes(data)) for name, data in (files or [])], lang=pick_lang(lang))
    status, payload = api.dispatch(_sandbox, req)
    if isinstance(payload, api.FileResponse):
        return status, "file", payload.data, payload.media_type, payload.filename, payload.inline
    return status, "json", json.dumps(payload, ensure_ascii=False), "", "", True

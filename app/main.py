"""Server runtime (FastAPI, the same framework as production).

The public demo runs on GitHub Pages without a server (see `browser.py`);
this module serves the very same UI and route table for local development
and container hosting. Each browser session gets its own sandbox.
"""
from __future__ import annotations

import copy
import secrets
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse as StarletteFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from . import api
from .i18n import pick_lang
from .sandbox import Sandbox, SandboxManager, count

WEB = Path(__file__).resolve().parent.parent / "web"
COOKIE = "demo_sid"

app = FastAPI(title="Portal Notas — demo", version="3.0.0",
              description="Supplier-invoice automation demo with fictional data. Every visitor gets an isolated "
                          "sandbox.")
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


class _TemplateCache:
    """Seeding runs the real pipeline over ~40 PDFs. Do it once and hand each
    new visitor a deep copy; refresh periodically so relative dates stay right."""

    def __init__(self, max_age: int = 1800):
        self.max_age = max_age
        self._sb: Optional[Sandbox] = None
        self._at = 0.0

    def fresh(self) -> Sandbox:
        if self._sb is None or time.monotonic() - self._at > self.max_age:
            self._sb, self._at = Sandbox(), time.monotonic()
        return copy.deepcopy(self._sb)


sandboxes = SandboxManager(factory=_TemplateCache().fresh)


@app.middleware("http")
async def session_cookie(request: Request, call_next):
    sid = request.cookies.get(COOKIE)
    new = not sid or len(sid) != 32
    request.state.sid = secrets.token_hex(16) if new else sid
    response = await call_next(request)
    if new:
        response.set_cookie(COOKIE, request.state.sid, httponly=True, samesite="lax", max_age=6 * 3600)
    count("http_requests_total")
    return response


@app.get("/")
def index():
    return StarletteFile(WEB / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "sandboxes": len(sandboxes)}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return api.metrics_text(len(sandboxes))


@app.post("/api/reset")
def reset(request: Request):
    sandboxes.reset(request.state.sid)
    return {"success": True}


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def api_proxy(request: Request, path: str):
    req = api.Request(method=request.method, path="/api/" + path, query=dict(request.query_params),
                      lang=pick_lang(request.headers.get("x-lang", "")))
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        req.form = {k: v for k, v in form.items() if isinstance(v, str)}
        req.files = [(v.filename or "file.pdf", await v.read()) for _, v in form.multi_items()
                     if not isinstance(v, str)]
    elif ctype.startswith("application/json"):
        req.json = await request.json()
    status, payload = api.dispatch(sandboxes.get(request.state.sid), req)
    if isinstance(payload, api.FileResponse):
        disposition = "inline" if payload.inline else "attachment"
        return Response(payload.data, media_type=payload.media_type,
                        headers={"Content-Disposition": f'{disposition}; filename="{payload.filename}"'})
    return JSONResponse(payload, status_code=status)

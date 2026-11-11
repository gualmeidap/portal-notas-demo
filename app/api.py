"""Framework-agnostic HTTP API.

One route table serves two runtimes:
* `app/main.py` — FastAPI on a server (local development, Docker);
* `app/browser.py` — the static build on GitHub Pages, where the same Python
  runs inside the visitor's browser (Pyodide / WebAssembly) and the page's
  `fetch` calls are routed here instead of over the network.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import unquote

from . import workflow as wf
from .i18n import T, localize
from .sandbox import METRICS, DemoError, Sandbox


@dataclass
class FileResponse:
    data: bytes
    media_type: str
    filename: str
    inline: bool = True


@dataclass
class Request:
    method: str
    path: str
    query: Dict[str, str]
    json: Any = None
    form: Optional[Dict[str, str]] = None
    files: Optional[List[Tuple[str, bytes]]] = None
    lang: str = "en"


Handler = Callable[[Sandbox, Request, Dict[str, str]], Any]
ROUTES: List[Tuple[str, re.Pattern, Handler]] = []


def route(method: str, pattern: str):
    regex = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$")

    def deco(fn: Handler) -> Handler:
        ROUTES.append((method, regex, fn))
        return fn
    return deco


def ok(payload: dict) -> dict:
    return {"success": True, **payload}


# ── reads ────────────────────────────────────────────────────────────────────
@route("GET", "/api/summary")
def _summary(sb, req, p):
    return sb.summary()


@route("GET", "/api/emails")
def _emails(sb, req, p):
    return sb.list_emails(req.query.get("view", "queue"))


@route("GET", "/api/emails/{email_id}")
def _email(sb, req, p):
    return sb.email_detail(p["email_id"])


@route("GET", "/api/emails/{email_id}/attachments/{name}")
def _attachment(sb, req, p):
    att = sb.attachment(p["email_id"], p["name"])
    if att.scanned:
        text = "[Scanned image without a text layer / Imagem digitalizada sem camada de texto. OCR:]\n\n" + att.ocr_text
        return FileResponse(text.encode("utf-8"), "text/plain; charset=utf-8", att.filename + ".txt")
    return FileResponse(att.pdf(), "application/pdf", att.filename)


@route("GET", "/api/emails/{email_id}/package.pdf")
def _package(sb, req, p):
    return FileResponse(sb.package_pdf(p["email_id"]), "application/pdf", f"pacote_{p['email_id']}.pdf")


@route("GET", "/api/emails/{email_id}/preview")
def _preview(sb, req, p):
    return sb.preview(p["email_id"])


@route("GET", "/api/outbox")
def _outbox(sb, req, p):
    return sb.outbox.messages


@route("GET", "/api/logs")
def _logs(sb, req, p):
    return list(sb.logs)


@route("GET", "/api/invoices")
def _invoices(sb, req, p):
    return sb.invoice_rows()


@route("GET", "/api/invoices/export.xlsx")
def _xlsx(sb, req, p):
    return FileResponse(sb.finance_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "notas_fiscais.xlsx", inline=False)


@route("GET", "/api/vendors")
def _vendors(sb, req, p):
    return sb.vendors()


@route("GET", "/api/samples")
def _samples(sb, req, p):
    return sorted(sb.samples())


@route("GET", "/api/samples/{name}")
def _sample(sb, req, p):
    data = sb.samples().get(p["name"])
    if data is None:
        raise DemoError(T("Sample not found.", "Exemplo não encontrado."), 404)
    return FileResponse(data, "application/pdf", p["name"], inline=False)


# ── writes ───────────────────────────────────────────────────────────────────
@route("POST", "/api/emails/{email_id}/confirm")
def _confirm(sb, req, p):
    return ok(sb.confirm(p["email_id"], (req.json or {}).get("records", [])))


@route("POST", "/api/emails/{email_id}/actions/{action}")
def _action(sb, req, p):
    return ok(sb.run_action(p["email_id"], p["action"]))


@route("POST", "/api/inbox/fetch")
def _fetch(sb, req, p):
    new = sb.fetch_inbox()
    return ok({"new": len(new), "message": T(f"{len(new)} new e-mail(s).", f"{len(new)} e-mail(s) novo(s).")
               if new else T("No new e-mails.", "Nenhum e-mail novo.")})


@route("POST", "/api/queue/process")
def _queue(sb, req, p):
    return ok(sb.process_queue())


@route("POST", "/api/monitor/{state}")
def _monitor(sb, req, p):
    if p["state"] not in ("start", "stop"):
        raise DemoError(T("state must be start or stop", "state deve ser start ou stop"), 404)
    sb.monitor = p["state"] == "start"
    sb.log("INFO", T(f"Automatic monitoring {'started' if sb.monitor else 'stopped'}.",
                     f"Monitoramento automático {'ligado' if sb.monitor else 'desligado'}."))
    return ok({"monitor": sb.monitor})


@route("POST", "/api/finance/send")
def _finance(sb, req, p):
    return ok(sb.send_finance_report())


@route("PUT", "/api/vendors/{key}")
def _upsert_vendor(sb, req, p):
    return ok({"vendor": sb.upsert_vendor(p["key"], req.json or {})})


@route("DELETE", "/api/vendors/{key}")
def _delete_vendor(sb, req, p):
    sb.delete_vendor(p["key"])
    return ok({})


@route("POST", "/api/vendors/ai-extract")
def _ai(sb, req, p):
    files = req.files or []
    pdf = files[0][1] if files else None
    if pdf and len(pdf) > 5 * 1024 * 1024:
        raise DemoError(T("File larger than 5 MB.", "Arquivo maior que 5 MB."), 413)
    return ok(sb.ai_vendor(pdf=pdf, email_id=(req.form or {}).get("email_id")))


@route("POST", "/api/manual/preview")
def _manual_preview(sb, req, p):
    files = req.files or []
    if len(files) > 6:
        raise DemoError(T("Up to 6 files per upload.", "Até 6 arquivos por envio."))
    return ok(sb.manual_preview(files))


@route("POST", "/api/manual/confirm")
def _manual_confirm(sb, req, p):
    body = req.json or {}
    return ok(sb.manual_confirm(body.get("token", ""), body.get("records", []), body.get("destination", "")))


def metrics_text(active_sandboxes: int) -> str:
    """Prometheus exposition format (production: scraped by Prometheus, charted in Grafana)."""
    lines = []
    for name, value in sorted(METRICS.items()):
        metric = f"invoice_demo_{name}"
        lines += [f"# TYPE {metric} counter", f"{metric} {value}"]
    lines += ["# TYPE invoice_demo_active_sandboxes gauge", f"invoice_demo_active_sandboxes {active_sandboxes}"]
    return "\n".join(lines) + "\n"


def dispatch(sb: Sandbox, req: Request) -> Tuple[int, Any]:
    """Run one request. Returns (status, payload); payload is a localized
    JSON-able object or a FileResponse."""
    for method, regex, fn in ROUTES:
        m = regex.match(req.path)
        if m and method == req.method:
            try:
                result = fn(sb, req, {k: unquote(v) for k, v in m.groupdict().items()})
            except DemoError as exc:
                return exc.status, {"success": False, "message": localize(exc.message, req.lang)}
            except wf.WorkflowError as exc:
                return 409, {"success": False, "message": localize(exc.args[0], req.lang)}
            if isinstance(result, FileResponse):
                return 200, result
            return 200, localize(result, req.lang)
    return 404, {"success": False, "message": localize(T("Not found.", "Não encontrado."), req.lang)}

"""Routes for the portal pages: overview, month by month, due dates, trash triage, reports, descriptions, settings.

Registered on the same route table as `api.py` (imported at the bottom of that module).
"""
from __future__ import annotations

import re

from .api import ok, route
from .i18n import T
from .sandbox import DemoError


def _clip(v, n: int = 200) -> str:
    return str(v or "").strip()[:n]


@route("GET", "/api/overview")
def _overview(sb, req, p):
    return sb.portal.overview(sb)


@route("GET", "/api/notifications")
def _notifications(sb, req, p):
    return sb.portal.notifications(sb)


@route("GET", "/api/search")
def _search(sb, req, p):
    q = _clip(req.query.get("q"), 80).lower()
    if len(q) < 2:
        return []
    hits = []
    for e in sb.emails.values():
        invs = [sb.invoices[i] for i in e.invoice_ids]
        blob = " ".join([e.sender, e.subject] + [f"{i['fornecedor']} {i['numero']}" for i in invs]).lower()
        if q in blob:
            hits.append(sb.email_view(e))
    hits.sort(key=lambda e: e["updated_at"], reverse=True)
    return hits[:12]


@route("GET", "/api/months")
def _months(sb, req, p):
    return sb.portal.months(sb)


@route("POST", "/api/months/mark")
def _months_mark(sb, req, p):
    b = req.json or {}
    return ok(sb.portal.mark_outside(_clip(b.get("name")), _clip(b.get("month"), 7)))


@route("GET", "/api/due")
def _due(sb, req, p):
    ym = req.query.get("month") or sb.portal.months(sb)["current"]
    if not re.fullmatch(r"\d{4}-\d{2}", ym) or not 1 <= int(ym[5:]) <= 12:
        raise DemoError(T("month must look like 2026-11.", "month deve ser como 2026-11."))
    return sb.portal.due_rows(sb, ym)


@route("PUT", "/api/due/{name}")
def _due_put(sb, req, p):
    rule = sb.portal.upsert_due(p["name"], req.json or {})
    if not rule:
        raise DemoError(T("Supplier name and a day between 1 and 31 are required.",
                          "Nome do fornecedor e um dia entre 1 e 31 são obrigatórios."), 422)
    sb.log("INFO", T(f"Due date saved for {rule['name']}: day {rule['day']}.",
                     f"Vencimento salvo para {rule['name']}: dia {rule['day']}."), who="admin.demo")
    return ok({})


@route("DELETE", "/api/due/{name}")
def _due_del(sb, req, p):
    if not sb.portal.delete_due(p["name"]):
        raise DemoError(T("Supplier not found.", "Fornecedor não encontrado."), 404)
    return ok({})


@route("POST", "/api/due/{name}/paid")
def _due_paid(sb, req, p):
    b = req.json or {}
    sb.portal.set_paid(p["name"], _clip(b.get("month"), 7), bool(b.get("paid")))
    return ok({})


@route("GET", "/api/triage")
def _triage(sb, req, p):
    return sb.portal.triage(sb)


@route("GET", "/api/history")
def _history(sb, req, p):
    q = req.query
    try:
        page = int(q.get("page") or 1)
    except ValueError:
        page = 1
    return sb.portal.history(sb, q.get("filter") or "all", page, _clip(q.get("category"), 30), _clip(q.get("q"), 80))


@route("GET", "/api/report/deadlines")
def _rep_deadlines(sb, req, p):
    return sb.portal.deadlines(sb)


@route("GET", "/api/report/senders")
def _rep_senders(sb, req, p):
    return sb.portal.senders(sb, "B" if req.query.get("group") == "B" else "A")


@route("GET", "/api/report/sender")
def _rep_sender(sb, req, p):
    return sb.portal.sender_emails(sb, _clip(req.query.get("name")))


@route("GET", "/api/report/types")
def _rep_types(sb, req, p):
    return sb.portal.email_types(sb, _clip(req.query.get("kind"), 30), _clip(req.query.get("q"), 80))


# ── descriptions ─────────────────────────────────────────────────────────────
@route("GET", "/api/descriptions")
def _desc(sb, req, p):
    g = "B" if req.query.get("group") == "B" else "A"
    mapping = [{"key": k, "default": v["default"], "rules": v["rules"]} for k, v in sb.portal.descriptions[g].items()]
    sample = {"numero": "4521", "fornecedor": "ValeLink Internet", "vencimento": "20/11/2026", "descricao": "",
              "vendor_key": "VALELINK", "valor_num": 1250.0}
    return {"mapping": mapping, "normalization": sb.portal.normalization, "pattern": sb.portal.pattern,
            "sample": sb.portal.describe(sample)}


@route("PUT", "/api/descriptions/{group}/{key}")
def _desc_put(sb, req, p):
    g = "B" if p["group"] == "B" else "A"
    b = req.json or {}
    default, key = _clip(b.get("default")), _clip(p["key"], 60).upper()
    if not key or not default:
        raise DemoError(T("Key and default description are required.", "Chave e descrição padrão são obrigatórias."), 422)
    rules = []
    for r in (b.get("rules") or [])[:10]:
        try:
            lo = float(r.get("min") or 0)
            hi = float(r["max"]) if r.get("max") not in (None, "") else None
        except (TypeError, ValueError):
            raise DemoError(T("Value rules need numeric limits.", "As regras de valor precisam de limites numéricos."), 422)
        if _clip(r.get("text")):
            rules.append({"min": lo, "max": hi, "text": T(_clip(r["text"]), _clip(r["text"]))})
    sb.portal.descriptions[g][key] = {"default": T(default, default), "rules": rules}
    return ok({})


@route("DELETE", "/api/descriptions/{group}/{key}")
def _desc_del(sb, req, p):
    sb.portal.descriptions["B" if p["group"] == "B" else "A"].pop(p["key"], None)
    return ok({})


@route("POST", "/api/normalization")
def _norm_add(sb, req, p):
    b = req.json or {}
    pat, name = _clip(b.get("pattern")).upper(), _clip(b.get("name"))
    if not pat or not name:
        raise DemoError(T("Both the text found and the normalized name are required.",
                          "O texto encontrado e o nome normalizado são obrigatórios."), 422)
    sb.portal.normalization = [r for r in sb.portal.normalization if r["pattern"] != pat] + [{"pattern": pat, "name": name}]
    return ok({})


@route("DELETE", "/api/normalization")
def _norm_del(sb, req, p):
    pat = _clip(req.query.get("pattern")).upper()
    sb.portal.normalization = [r for r in sb.portal.normalization if r["pattern"] != pat]
    return ok({})


@route("PUT", "/api/pattern")
def _pattern(sb, req, p):
    pat = _clip((req.json or {}).get("pattern"), 300)
    if "{numero}" not in pat:
        raise DemoError(T("The pattern must contain {numero}.", "O padrão precisa conter {numero}."), 422)
    sb.portal.pattern = pat
    return ok({})


# ── settings ─────────────────────────────────────────────────────────────────
@route("GET", "/api/settings")
def _settings(sb, req, p):
    po = sb.portal
    return {"settings": po.settings, "direct_rules": po.direct_rules, "purchasing_rules": po.purchasing_rules,
            "removal": po.removal, "teams": po.teams, "tickets": po.tickets,
            "suppliers": sorted({v["fornecedor"] for v in sb.rules["vendor_map"].values()})}


_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,120}\.[A-Za-z]{2,}$")


def _addr(v, label: str) -> str:
    v = _clip(v, 120).lower()
    if not _EMAIL.match(v):
        raise DemoError(T(f"'{label}' must be an e-mail address.", f"'{label}' deve ser um endereço de e-mail."), 422)
    return v


@route("PUT", "/api/settings/sectors")
def _sectors(sb, req, p):
    b = req.json or {}
    new = {}
    for sector in ("purchasing", "fiscal"):
        cur = b.get(sector) or {}
        new[sector] = {"receives": _addr(cur.get("receives"), sector),
                       "also": [_addr(x, sector) for x in (cur.get("also") or [])][:10]}
    sb.portal.settings.update(new)
    sb.log("INFO", T("Purchasing and Fiscal addresses updated.", "Endereços de Compras e Fiscal atualizados."),
           area="Settings", who="admin.demo")
    return ok({})


@route("POST", "/api/settings/removal/{kind}")
def _removal_add(sb, req, p):
    if p["kind"] not in sb.portal.removal:
        raise DemoError(T("Unknown list.", "Lista desconhecida."), 404)
    v = _clip((req.json or {}).get("value"), 100).lower()
    if len(v) < 3:
        raise DemoError(T("Type at least 3 characters.", "Digite pelo menos 3 caracteres."), 422)
    lst = sb.portal.removal[p["kind"]]
    if v not in lst:
        lst.append(v)
    removed = 0
    if p["kind"] in ("senders", "subjects"):
        removed = sum(sb.apply_removal_rules(e) for e in list(sb.emails.values()))
    return ok({"removed": removed, "message": T(f"Rule saved. {removed} e-mail(s) in the queue removed now.",
                                                f"Regra salva. {removed} e-mail(s) da fila removido(s) agora.")})


@route("DELETE", "/api/settings/removal/{kind}")
def _removal_del(sb, req, p):
    if p["kind"] not in sb.portal.removal:
        raise DemoError(T("Unknown list.", "Lista desconhecida."), 404)
    v = _clip(req.query.get("value"), 100).lower()
    sb.portal.removal[p["kind"]] = [x for x in sb.portal.removal[p["kind"]] if x != v]
    return ok({})


def _upsert_rule(sb, req, store: list, dest_field: str, extra: dict):
    b = req.json or {}
    supplier = _clip(b.get("supplier"), 80)
    if not supplier:
        raise DemoError(T("Choose the supplier.", "Escolha o fornecedor."), 422)
    row = {"id": _clip(b.get("id"), 12) or sb.portal.new_id(), "supplier": supplier, "note": _clip(b.get("note")),
           dest_field: _addr(b.get(dest_field), dest_field), **extra}
    store[:] = [r for r in store if r["id"] != row["id"] and r["supplier"].lower() != supplier.lower()] + [row]
    return ok({"id": row["id"]})


@route("PUT", "/api/settings/direct")
def _direct_put(sb, req, p):
    b = req.json or {}
    how = b.get("how") if b.get("how") in ("process", "forward") else "process"
    after = b.get("after") if b.get("after") in ("close", "wait_cover") else "close"
    return _upsert_rule(sb, req, sb.portal.direct_rules, "dest", {"how": how, "after": after})


@route("DELETE", "/api/settings/direct/{rid}")
def _direct_del(sb, req, p):
    sb.portal.direct_rules[:] = [r for r in sb.portal.direct_rules if r["id"] != p["rid"]]
    return ok({})


@route("PUT", "/api/settings/purchasing-rule")
def _buy_put(sb, req, p):
    return _upsert_rule(sb, req, sb.portal.purchasing_rules, "to", {})


@route("DELETE", "/api/settings/purchasing-rule/{rid}")
def _buy_del(sb, req, p):
    sb.portal.purchasing_rules[:] = [r for r in sb.portal.purchasing_rules if r["id"] != p["rid"]]
    return ok({})


@route("PUT", "/api/settings/tickets")
def _tickets_put(sb, req, p):
    b = req.json or {}
    g = sb.portal.tickets
    if b.get("mode") in ("off", "simulation", "on"):
        g["mode"] = b["mode"]
    for k in ("open_days_before", "followup_days_after", "ignore_older_than"):
        try:
            g[k] = max(0, min(365, int(b.get(k, g[k]))))
        except (TypeError, ValueError):
            raise DemoError(T("Days must be whole numbers.", "Os dias devem ser números inteiros."), 422)
    if re.fullmatch(r"\d{2}:\d{2}", str(b.get("check_at") or "")):
        g["check_at"] = b["check_at"]
    return ok({})


@route("GET", "/api/settings/tickets/preview")
def _tickets_prev(sb, req, p):
    return sb.portal.tickets_preview(sb)


@route("POST", "/api/settings/tickets/test")
def _tickets_test(sb, req, p):
    sb.log("INFO", T("Ticket service connection test: OK (mock).", "Teste de conexão com o service desk: OK (simulado)."),
           area="Service desk", who="admin.demo")
    return ok({"message": T("Connection OK (mock service).", "Conexão OK (serviço simulado).")})


@route("GET", "/api/settings/teams/preview")
def _teams_prev(sb, req, p):
    return sb.portal.teams_preview(sb)


@route("POST", "/api/settings/teams/send")
def _teams_send(sb, req, p):
    sb.portal.teams["last_sent"] = sb.now().isoformat(timespec="seconds")
    sb.log("SUCCESS", T("Daily summary card posted to Teams (mock).", "Cartão do resumo diário publicado no Teams (simulado)."),
           area="Teams", who="admin.demo")
    return ok({"message": T("Card posted to the mock channel.", "Cartão publicado no canal simulado.")})

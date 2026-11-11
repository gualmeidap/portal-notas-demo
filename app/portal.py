"""Portal-wide views that sit around the invoice workflow.

Everything here is fictional demo data. The production portal tracks which
supplier invoices are *expected* each month (a due day per supplier), shows a
month-by-month grid, triages the trash, reports what each sender sends and
keeps the operational settings (who receives what, direct-send rules, ...).

Read models return plain data (codes, numbers, dates) and the page formats the
text in the visitor's language; operator-facing messages stay `T(en, pt)`.
"""
from __future__ import annotations

import calendar
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from . import workflow as wf
from .i18n import T
from .samples import FISCAL_ADDR, MAILBOX_ADDR, PURCHASING_ADDR

# ── trash triage ─────────────────────────────────────────────────────────────
CATEGORIES = {
    "scam": {"label": T("Suspected scam", "Suspeito de golpe"), "tone": "red",
             "action": T("Block the sender and alert security", "Bloquear o remetente e avisar a segurança")},
    "newsletter": {"label": T("Newsletter and marketing", "Newsletter e marketing"), "tone": "blue",
                   "action": T("Unsubscribe and ignore the sender", "Cancelar inscrição e ignorar o remetente")},
    "other_group": {"label": T("Other group's mailbox", "Caixa de outro grupo"), "tone": "orange",
                    "action": T("Forwarding rule to the other group's mailbox",
                                "Regra de encaminhamento para a caixa do outro grupo")},
    "billing_reminder": {"label": T("Payment reminder", "Lembrete de cobrança"), "tone": "green",
                         "action": T("Link to the package, without going through the queue",
                                     "Vincular ao pacote, sem passar pela fila")},
    "handled": {"label": T("Already handled: outside, duplicates and replies",
                           "Já tratado: por fora, duplicadas e respostas"),
                "tone": "green", "action": T("Archive automatically", "Arquivar sozinho")},
    "informative": {"label": T("Supplier notice", "Informativo do fornecedor"), "tone": "green",
                    "action": T("Mark as informational", "Marcar como informativa")},
    "account_system": {"label": T("Account, system and domain", "Conta, sistema e domínio"), "tone": "green",
                       "action": T("Always ignore (or forward to IT)", "Ignorar sempre (ou encaminhar ao TI)")},
    "other": {"label": T("Other", "Outros"), "tone": "gray", "action": T("Review only", "Só revisar")},
}
DECISION = ("scam", "newsletter", "other_group")

_KEYWORDS = [
    ("scam", ("urgente", "premio", "prêmio", "ganhou", "será bloqueada", "verifique sua conta")),
    ("newsletter", ("webinar", "newsletter", "ofertas", "congresso", "inscreva", "inscrições")),
    ("other_group", ("grupo b", "group b")),
    ("billing_reminder", ("lembrete", "vencerá", "aviso de pendência", "fatura vence")),
    ("account_system", ("domínio", "dominio", "senha", "certificado", "painel")),
    ("informative", ("informativo", "comunicado", "manutenção")),
    ("handled", ("enc:", "res:", "re:", "duplicad")),
]


def categorize(sender: str, subject: str) -> str:
    text = f"{sender} {subject}".lower()
    for key, words in _KEYWORDS:
        if any(w in text for w in words):
            return key
    return "other"


_TRASH = {
    "scam": (6, ["Prêmio Express", "Aviso de Conta Segura", "Recebimento Imediato"],
             ["URGENTE: sua conta será bloqueada hoje", "Você ganhou um prêmio: confirme agora",
              "Verifique sua conta para evitar suspensão"]),
    "newsletter": (18, ["Tech Weekly", "Loja Mais Ofertas", "Congresso Educação Digital", "Webinars Gestão"],
                   ["Webinar gratuito: gestão de contratos", "As ofertas da semana chegaram",
                    "Inscrições abertas: congresso 2027", "Newsletter de novembro"]),
    "other_group": (14, ["Faturamento Grupo B", "Telecom Grupo B", "Compras Grupo B"],
                    ["ENC: Fatura disponível - Grupo B", "Nota fiscal Grupo B - competência anterior",
                     "Boleto Grupo B em aberto"]),
    "billing_reminder": (22, ["FibraNorte Telecom", "ValeLink Internet", "PontoCom Fibra", "Cobrança Fácil"],
                         ["Lembrete: sua fatura vence em 3 dias", "Aviso de pendência de pagamento",
                          "Sua mensalidade vencerá em 5 dias"]),
    "handled": (40, ["Mesa de Compras", "Mesa Fiscal", "Aurora Net Provedor", "SinalMax Telecom"],
                ["ENC: Nota Fiscal Eletrônica", "RES: Faturas - mês anterior", "ENC: Alinhamento de pagamentos"]),
    "informative": (8, ["NuvemCerta Hosting", "AssinaFácil", "SinalMax Telecom"],
                    ["Informativo: manutenção programada", "Comunicado importante aos clientes"]),
    "account_system": (18, ["NomeRaiz Domínios", "Painel de Hospedagem", "Console Cloud"],
                       ["Domínio expira em 30 dias", "Sua senha foi alterada", "Renovação de certificado"]),
    "other": (12, ["Contato Geral", "Atendimento", "Notificação ao Usuário"],
              ["Assunto sem classificação", "Mensagem automática", "Confirmação de recebimento"]),
}
_REASONS = {
    "scam": T("Phishing pattern in the subject", "Padrão de phishing no assunto"),
    "newsletter": T("Sender is a mass mailer", "Remetente é de envio em massa"),
    "other_group": T("Addressed to another group", "Endereçado a outro grupo"),
    "billing_reminder": T("Reminder for an invoice already in the portal", "Lembrete de fatura que já está no portal"),
    "handled": T("Duplicate of a package already processed", "Duplicata de pacote já processado"),
    "informative": T("No document attached", "Sem documento anexado"),
    "account_system": T("Automatic notice from a system", "Aviso automático de sistema"),
    "other": "",
}

# Expected invoices per supplier: (name, day offset from today, unit, kind, days the NF comes before the due date,
# typical amount, note). The due day is today+offset in the current month, so the demo always has something late,
# something due soon and something on time, whatever day it is opened. kind: tracked | on_demand | outside.
_SUPPLIERS = [
    ("FibraNorte Telecom", -4, "North Campus", "tracked", 5, 1450, T("Normal flow (Purchasing → Fiscal).", "Fluxo normal (Compras → Fiscal).")),
    ("Aurora Net Provedor", -1, "South Campus", "tracked", 3, 2310, T("Invoice and boleto come together in one PDF.", "Nota e boleto chegam juntos em um PDF.")),
    ("PontoCom Fibra", 2, "Downtown Campus", "tracked", 6, 980, T("Boleto first; the invoice comes a few days later.", "Boleto primeiro; a nota chega dias depois.")),
    ("SinalMax Telecom", 4, "West Campus", "tracked", 4, 3120, T("Scanned invoice: goes through OCR.", "Nota digitalizada: passa pelo OCR.")),
    ("ValeLink Internet", 9, "East Campus", "tracked", 7, 1250, T("Normal flow.", "Fluxo normal.")),
    ("NuvemCerta Hosting", 13, "Headquarters", "tracked", 2, 760, T("Goes directly to Fiscal.", "Vai direto para o Fiscal.")),
    ("AssinaFácil", 17, "Headquarters", "tracked", 5, 540, T("Protected PDF: forwarded as it is.", "PDF protegido: encaminhado como está.")),
    ("NomeRaiz Domínios", 19, "Headquarters", "tracked", 1, 290, T("Yearly domains are billed in November.", "Domínios anuais são cobrados em novembro.")),
    ("Cinza Cloud", -6, "Headquarters", "tracked", 4, 4890, T("Usage-based: the amount varies every month.", "Cobrança por uso: o valor varia todo mês.")),
    ("DataPorto Links", -2, "North Campus", "tracked", 5, 1790, T("Two links on one invoice.", "Dois links na mesma nota.")),
    ("Lumen Papelaria", -3, "Headquarters", "tracked", 8, 620, T("Irregular due date.", "Vencimento irregular.")),
    ("OfficeTech Software", 11, "Headquarters", "tracked", 6, 2200, T("Licenses billed per semester.", "Licenças cobradas por semestre.")),
    ("Vento Wireless", 15, "West Campus", "tracked", 4, 1110, T("Normal flow.", "Fluxo normal.")),
    ("Pixel Gráfica", 10, "Headquarters", "on_demand", 0, 0, T("Only bills when there is use (printing jobs).", "Só fatura quando há uso (serviços de impressão).")),
    ("Luz do Vale Energia", 8, "Downtown Campus", "outside", 0, 0, T("The invoice does not come by e-mail: paid from the supplier's site.", "A nota não vem por e-mail: paga pelo site do fornecedor.")),
]
_UNIT_SLUG = {"North Campus": "north", "South Campus": "south", "East Campus": "east", "West Campus": "west",
              "Downtown Campus": "downtown", "Headquarters": "hq"}
_ARRIVED_NOW = {"ValeLink Internet", "NuvemCerta Hosting", "Cinza Cloud", "DataPorto Links", "OfficeTech Software"}


def month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def shift_month(ym: str, n: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    i = y * 12 + (m - 1) + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def due_date(day: int, ym: str) -> date:
    y, m = int(ym[:4]), int(ym[5:7])
    return date(y, m, min(day, calendar.monthrange(y, m)[1]))


def _parse(d: str) -> Optional[date]:
    try:
        return datetime.strptime(d, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


class Portal:
    """State for the portal pages. One per sandbox."""

    def __init__(self, today: date):
        self.today = today
        ym = month_key(today)
        self.rules: List[dict] = []
        for i, (name, off, unit, kind, nf_off, base, note) in enumerate(_SUPPLIERS):
            day = max(1, min(28, today.day + off))
            self.rules.append({
                "name": name, "day": day, "unit": unit, "group": "A", "track": kind != "outside",
                "on_demand": kind == "on_demand", "dest": f"purchasing.{_UNIT_SLUG[unit]}@university.example",
                "note": note, "nf_offset": nf_off, "team_informed": i % 4 == 0, "base": base,
            })
        self.arrivals: Dict[tuple, dict] = {}
        self.outside: set = {("Cinza Cloud", shift_month(ym, -1)), ("DataPorto Links", shift_month(ym, -2))}
        self.paid: set = set()
        for i, r in enumerate(self.rules):
            if not r["track"] or r["on_demand"]:
                continue
            for back in (2, 1):
                if (r["name"], shift_month(ym, -back)) not in self.outside:
                    self._arrive(r["name"], shift_month(ym, -back), r, i, None)
            if r["name"] in _ARRIVED_NOW:
                self._arrive(r["name"], ym, r, i, None)
        self.last_sync = datetime.now().replace(microsecond=0)

        self.settings = {
            "mailbox": MAILBOX_ADDR, "environment": "production",
            "purchasing": {"receives": PURCHASING_ADDR, "also": ["purchasing.test@university.example"]},
            "fiscal": {"receives": FISCAL_ADDR, "also": ["fiscal.test@university.example"]},
        }
        self.direct_rules: List[dict] = []
        self.purchasing_rules: List[dict] = []
        self.removal = {"senders": [], "subjects": [], "never_point": []}
        self.teams = {"enabled": True, "channel": "#invoice-desk", "last_sent": None,
                      "buttons": ["Open portal", "Month by month"]}
        self.tickets = {"mode": "simulation", "user": "portal.bot", "category": "Supplier invoices",
                     "recipients": "it.contracts@university.example", "open_days_before": 7,
                     "followup_days_after": 3, "ignore_older_than": 45, "check_at": "09:00"}
        self.descriptions = {
            "A": {"FIBRANORTE": {"default": T("Communication services", "Serviços de comunicação"), "rules": []},
                  "AURORA NET": {"default": T("Internet link", "Link de internet"), "rules": []},
                  "VALELINK": {"default": T("Internet link", "Link de internet"), "rules": []},
                  "SINALMAX": {"default": T("Communication services", "Serviços de comunicação"), "rules": []},
                  "PONTOCOM FIBRA": {"default": T("Fiber connectivity", "Conectividade em fibra"), "rules": []},
                  "NUVEMCERTA": {"default": T("Hosting and cloud services", "Serviços de hospedagem e nuvem"),
                                 "rules": [{"min": 5000.0, "max": None,
                                            "text": T("Hosting (high usage)", "Hospedagem (alto consumo)")}]},
                  "ASSINAFACIL": {"default": T("Document management", "Gestão de documentos"), "rules": []},
                  "NOMERAIZ DOMINIOS": {"default": T("Domain registration", "Registro de domínios"), "rules": []}},
            "B": {"GRUPO B LOGISTICA": {"default": T("Logistics services", "Serviços de logística"), "rules": []},
                  "GRUPO B SEGUROS": {"default": T("Insurance", "Seguros"), "rules": []}},
        }
        self.normalization = [
            {"pattern": "FIBRANORTE TELECOM LTDA", "name": "FibraNorte Telecom"},
            {"pattern": "AURORA NET PROVEDOR DE INTERNET", "name": "Aurora Net Provedor"},
            {"pattern": "VALELINK INTERNET EIRELI", "name": "ValeLink Internet"},
        ]
        self.pattern = "PAGAMENTO DA NF {numero} - {descricao} - {fornecedor} - VENC. {vencimento}"

    # ── arrivals ─────────────────────────────────────────────────────────────
    def _arrive(self, name: str, ym: str, rule: dict, idx: int, email_id: Optional[str]) -> None:
        due = due_date(rule["day"], ym)
        issued = due - timedelta(days=rule["nf_offset"] + 1)
        self.arrivals.setdefault((name, ym), {
            "email_id": email_id, "numero": str(4000 + idx * 37 + int(ym[5:7])),
            "valor": float(rule["base"] + (idx * 53 + int(ym[5:7]) * 17) % 300), "emissao": issued,
            "boleto_at": issued + timedelta(days=1), "vencimento": due,
        })

    def record_arrival(self, name: str, venc: str, numero: str, valor: float, issued: str, email_id: str) -> None:
        due = _parse(venc)
        ym = month_key(due) if due else month_key(self.today)
        self.arrivals[(name, ym)] = {
            "email_id": email_id, "numero": numero, "valor": valor, "emissao": _parse(issued) or self.today,
            "boleto_at": self.today, "vencimento": due or self.today,
        }

    def rule(self, name: str) -> Optional[dict]:
        return next((r for r in self.rules if r["name"].lower() == name.lower()), None)

    def situation(self, sb, rule: dict, ym: str) -> dict:
        due = due_date(rule["day"], ym)
        delta = (due - self.today).days
        key = (rule["name"], ym)
        arr = self.arrivals.get(key)
        if key in self.paid:
            state = "paid"
        elif rule["on_demand"]:
            state = "on_demand"
        elif not rule["track"]:
            state = "outside_portal"
        elif arr:
            em = sb.emails.get(arr["email_id"]) if arr["email_id"] else None
            state = "received" if em is None or em.status == wf.DONE else "in_progress"
        elif key in self.outside:
            state = "done_outside"
        elif delta < 0:
            state = "late"
        elif delta <= 7:
            state = "soon"
        else:
            state = "on_time"
        return {"state": state, "delta": delta, "due": due.isoformat(), "arrival": arr}

    # ── views ────────────────────────────────────────────────────────────────
    def months(self, sb) -> dict:
        ym = month_key(self.today)
        cols = [shift_month(ym, n) for n in (-2, -1, 0, 1)]
        tracked = [r for r in self.rules if r["track"] and not r["on_demand"]]
        rows, cards = [], {c: {"arrived": 0, "outside": 0, "total": len(tracked)} for c in cols}
        cell_of = {"received": "arrived", "in_progress": "arrived", "paid": "arrived", "done_outside": "outside",
                   "late": "missed", "soon": "soon", "on_time": "pending"}
        for r in self.rules:
            is_tracked = r["track"] and not r["on_demand"]
            cells = {}
            for c in cols:
                s = self.situation(sb, r, c)["state"]
                cell = cell_of.get(s, "dash") if is_tracked else "dash"
                cells[c] = cell
                if is_tracked and cell in ("arrived", "outside"):
                    cards[c]["arrived"] += 1
                    cards[c]["outside"] += cell == "outside"
            rows.append({"name": r["name"], "day": r["day"], "cells": cells, "tracked": is_tracked})
        rows.sort(key=lambda x: (not x["tracked"], x["day"]))
        return {"months": cols, "current": ym, "cards": cards, "rows": rows}

    def mark_outside(self, name: str, ym: str) -> dict:
        key = (name, ym)
        if key in self.arrivals:
            return {"marked": False}
        self.outside ^= {key}
        return {"marked": key in self.outside}

    def due_rows(self, sb, ym: str) -> dict:
        rows = []
        for r in sorted(self.rules, key=lambda x: x["day"]):
            s = self.situation(sb, r, ym)
            rows.append({**{k: r[k] for k in ("name", "day", "unit", "dest", "note", "track", "on_demand")},
                         "state": s["state"], "delta": s["delta"], "due": s["due"]})
        c = Counter(x["state"] for x in rows)
        return {"month": ym, "rows": rows, "counts": {
            "late": c["late"], "soon": c["soon"], "received": c["received"] + c["in_progress"] + c["paid"],
            "on_time": c["on_time"], "on_demand": c["on_demand"], "outside_portal": c["outside_portal"]}}

    def upsert_due(self, name: str, data: dict) -> Optional[dict]:
        name = str(data.get("name") or name).strip()
        try:
            day = int(data.get("day") or 0)
        except (TypeError, ValueError):
            day = 0
        if not name or not 1 <= day <= 31:
            return None
        fields = {"name": name, "day": day, "unit": str(data.get("unit") or "").strip(),
                  "dest": str(data.get("dest") or "").strip(),
                  "track": bool(data.get("track", True)), "on_demand": bool(data.get("on_demand", False))}
        cur = self.rule(name)
        note = data.get("note")
        if cur:
            cur.update(fields)
            if isinstance(note, str):
                cur["note"] = note
            return cur
        new = {**fields, "note": str(note or ""), "group": "A", "nf_offset": 5, "team_informed": False, "base": 800}
        self.rules.append(new)
        return new

    def delete_due(self, name: str) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if r["name"] != name]
        return len(self.rules) != before

    def set_paid(self, name: str, ym: str, paid: bool) -> None:
        (self.paid.add if paid else self.paid.discard)((name, ym))

    def overview(self, sb) -> dict:
        ym = month_key(self.today)
        due = self.due_rows(sb, ym)
        tracked = [x for x in due["rows"] if x["track"] and not x["on_demand"]]
        in_progress = sum(1 for x in tracked if x["state"] == "in_progress")
        completed = sum(1 for x in tracked if x["state"] in ("received", "paid"))
        missing = [x for x in tracked if x["state"] in ("late", "soon", "on_time")]
        month_emails = [e for e in sb.emails.values() if e.invoice_ids and
                        sb.invoices[e.invoice_ids[0]]["extracted_at"][:7] == ym]
        per_day = Counter(int(sb.invoices[e.invoice_ids[0]]["extracted_at"][8:10]) for e in month_emails)
        days = [{"day": d, "n": per_day.get(d, 0)} for d in range(1, self.today.day + 1)]
        n_auto = sum(1 for e in month_emails if e.process_type == "Automatic")
        n_bulk = sum(1 for e in month_emails if len(e.invoice_ids) > 1)
        groups = Counter()
        for e in sb.emails.values():
            if e.status == wf.DELETED:
                continue
            if e.status in wf.QUEUE:
                groups["pending"] += 1
            elif e.status == wf.AWAITING_PURCHASING:
                groups["awaiting_purchasing"] += 1
            elif e.status in (wf.READY_FOR_FISCAL, wf.AWAITING_FISCAL, wf.AWAITING_COVER):
                groups["awaiting_fiscal"] += 1
            elif e.status == wf.READY_TO_PRINT:
                groups["ready_to_print"] += 1
            elif e.status == wf.DONE and e.timeline[-1]["ts"][:7] == ym:
                groups["completed"] += 1
        return {
            "month": ym, "processed": len(month_emails), "daily": days,
            "auto": n_auto, "manual": len(month_emails) - n_auto, "bulk": n_bulk, "single": len(month_emails) - n_bulk,
            "last_sync": self.last_sync.isoformat(), "groups": dict(groups),
            "in_queue": sum(1 for e in sb.emails.values() if e.status not in wf.CLOSED),
            "completed_month": groups.get("completed", 0),
            "calendar": {"counts": {"late": due["counts"]["late"], "soon": due["counts"]["soon"],
                                    "on_time": due["counts"]["on_time"], "in_progress": in_progress,
                                    "completed": completed},
                         "suppliers": len(tracked), "missing": missing[:5], "missing_total": len(missing),
                         "ticket_mode": self.tickets["mode"]},
        }

    def notifications(self, sb) -> dict:
        due = self.due_rows(sb, month_key(self.today))
        items = sorted((x for x in due["rows"] if x["state"] in ("late", "soon")), key=lambda x: x["delta"])
        return {"count": len(items), "items": items[:8]}

    # ── trash triage / history ───────────────────────────────────────────────
    def category_of(self, e) -> str:
        return e.category or categorize(e.sender, e.subject)

    def triage(self, sb) -> dict:
        trash = [e for e in sb.emails.values() if e.status == wf.DELETED]
        by_cat: Dict[str, List] = {k: [] for k in CATEGORIES}
        for e in trash:
            by_cat[self.category_of(e)].append(e)
        total = len(trash)
        noted = sum(1 for e in trash if e.reason)
        cats = []
        for key, info in CATEGORIES.items():
            top = Counter(e.sender for e in by_cat[key]).most_common(4)
            cats.append({"key": key, "label": info["label"], "tone": info["tone"], "action": info["action"],
                         "count": len(by_cat[key]), "top": [{"sender": s, "n": n} for s, n in top]})
        return {"total": total, "unnoted_pct": round(100 * (total - noted) / total) if total else 0,
                "decision": sum(len(by_cat[k]) for k in DECISION), "review": len(by_cat["other"]), "categories": cats}

    def history(self, sb, flt: str, page: int, category: str, q: str, size: int = 10) -> dict:
        items = [e for e in sb.emails.values() if e.status in wf.CLOSED]
        total_all = len(items)
        n_done = sum(1 for e in items if e.status == wf.DONE)
        if flt == "done":
            items = [e for e in items if e.status == wf.DONE]
        elif flt == "deleted":
            items = [e for e in items if e.status == wf.DELETED]
        if category:
            items = [e for e in items if e.status == wf.DELETED and self.category_of(e) == category]
        if q:
            ql = q.lower()
            items = [e for e in items if ql in e.sender.lower() or ql in e.subject.lower()]
        items.sort(key=lambda e: e.timeline[-1]["ts"], reverse=True)
        pages = max(1, -(-len(items) // size))
        page = max(1, min(page, pages))
        rows = []
        for e in items[(page - 1) * size: page * size]:
            invs = [sb.invoices[i] for i in e.invoice_ids]
            cat = self.category_of(e) if e.status == wf.DELETED else ""
            rows.append({"id": e.id, "sender": e.sender, "supplier": invs[0]["fornecedor"] if invs else "",
                         "subject": e.subject, "status": e.status, "manual": e.process_type == "Manual",
                         "category": cat, "reason": e.reason or "", "closed_at": e.timeline[-1]["ts"],
                         "tone": CATEGORIES[cat]["tone"] if cat else "",
                         "category_label": CATEGORIES[cat]["label"] if cat else ""})
        return {"rows": rows, "page": page, "pages": pages, "total": len(items),
                "counts": {"all": total_all, "done": n_done, "deleted": total_all - n_done}}

    # ── removal rules ────────────────────────────────────────────────────────
    def matches_removal(self, sender: str, subject: str) -> Optional[str]:
        s = sender.lower()
        for rule in self.removal["senders"]:
            r = rule.lower()
            if s == r or s.endswith("@" + r) or s.endswith("." + r):
                return rule
        for rule in self.removal["subjects"]:
            if rule.lower() in subject.lower():
                return rule
        return None

    # ── reports ──────────────────────────────────────────────────────────────
    def deadlines(self, sb) -> dict:
        ym = month_key(self.today)
        out = []
        for r in sorted([x for x in self.rules if x["track"] and not x["on_demand"]], key=lambda x: x["name"]):
            months = []
            for m in (ym, shift_month(ym, 1)):
                s = self.situation(sb, r, m)
                due = date.fromisoformat(s["due"])
                arr = s["arrival"]
                expected = due - timedelta(days=r["nf_offset"])
                months.append({
                    "ym": m, "due": s["due"], "delta": s["delta"],
                    "nf": {"arrived": bool(arr), "number": arr and arr["numero"], "amount": arr and arr["valor"],
                           "issued": arr and arr["emissao"].isoformat(), "expected": expected.isoformat(),
                           "until": (expected + timedelta(days=3)).isoformat(),
                           "late": not arr and expected < self.today},
                    "boleto": {"arrived": bool(arr), "at": arr and arr["boleto_at"].isoformat(),
                               "amount": arr and arr["valor"], "due": arr and arr["vencimento"].isoformat(),
                               "delta": arr and (arr["vencimento"] - self.today).days},
                })
            prev = self.arrivals.get((r["name"], ym)) or self.arrivals.get((r["name"], shift_month(ym, -1)))
            em = sb.emails.get(prev["email_id"]) if prev and prev["email_id"] else None
            tag = "in_queue" if em and em.status in wf.QUEUE else "in_workflow" if em and em.status in wf.BOARD else "done"
            out.append({"name": r["name"], "day": r["day"], "nf_offset": r["nf_offset"],
                        "team_informed": r["team_informed"], "months": months,
                        "last": prev and {"number": prev["numero"], "delta": (prev["vencimento"] - self.today).days,
                                          "tag": tag},
                        "outside": any(k[0] == r["name"] for k in self.outside)})
        return {"month": ym, "read_emails": len(sb.emails), "rows": out}

    def _kind_of(self, e) -> str:
        names = " ".join(a.filename.lower() for a in e.attachments)
        nf = any(w in names for w in ("nf", "nota", "fatura"))
        bol = "boleto" in names
        return "both" if nf and bol else "nf" if nf else "boleto" if bol else "none"

    def senders(self, sb, group: str) -> dict:
        emails = [e for e in sb.emails.values() if (self.category_of(e) == "other_group") == (group == "B")]
        names = {r["name"].lower() for r in self.rules}
        domains = [v["sender_domain"] for v in sb.rules["vendor_map"].values() if v.get("sender_domain")]
        by: Dict[str, List] = {}
        for e in emails:
            by.setdefault(e.sender, []).append(e)
        sup, other = [], []
        for sender, es in by.items():
            kinds = Counter(self._kind_of(e) for e in es)
            how = "attachment" if any(e.attachments for e in es) else \
                "link" if any("https://" in e.body for e in es) else "none"
            row = {"sender": sender, "emails": len(es), "nf": kinds["nf"] + kinds["both"],
                   "boleto": kinds["boleto"] + kinds["both"],
                   "kind": "both" if kinds["both"] else "nf" if kinds["nf"] else "boleto" if kinds["boleto"] else "none",
                   "how": how}
            is_sup = sender.lower() in names or any(sender.lower().endswith(d) for d in domains)
            (sup if is_sup else other).append(row)
        return {"suppliers": sorted(sup, key=lambda x: -x["emails"]), "others": sorted(other, key=lambda x: -x["emails"])}

    def sender_emails(self, sb, sender: str) -> List[dict]:
        es = sorted((e for e in sb.emails.values() if e.sender == sender), key=lambda e: e.received_at, reverse=True)
        return [{"id": e.id, "subject": e.subject, "received_at": e.received_at.isoformat(), "status": e.status,
                 "kind": self._kind_of(e)} for e in es[:30]]

    def email_types(self, sb, kind: str, q: str) -> dict:
        rows = []
        for e in sorted(sb.emails.values(), key=lambda e: e.received_at, reverse=True):
            if e.status == wf.DELETED:
                typ = self.category_of(e)
                why = e.reason or T("Keywords in the subject", "Palavras-chave no assunto")
                source = "rule" if e.reason else "ai"
            else:
                typ = "invoice"
                why = T("Has an invoice or boleto attached", "Tem nota ou boleto anexado") if e.attachments else \
                    T("Link to the invoice in the body", "Link para a nota no corpo do e-mail")
                source = "rule"
            if (kind and kind != typ) or (q and q.lower() not in f"{e.sender} {e.subject}".lower()):
                continue
            rows.append({"id": e.id, "sender": e.sender, "subject": e.subject, "received_at": e.received_at.isoformat(),
                         "type": typ,
                         "type_label": CATEGORIES[typ]["label"] if typ in CATEGORIES else T("Real invoice", "Nota de verdade"),
                         "source": source, "why": why, "status": e.status})
        counts = Counter(r["type"] for r in rows)
        return {"rows": rows[:60], "total": len(rows), "counts": dict(counts),
                "labels": {k: v["label"] for k, v in CATEGORIES.items()}}

    # ── descriptions ─────────────────────────────────────────────────────────
    def describe(self, inv: dict) -> str:
        key = inv.get("vendor_key") or ""
        entry = next((g[key] for g in self.descriptions.values() if key in g), None)
        base = inv.get("descricao") or ""
        if entry:
            base = entry["default"].pt
            for rule in entry["rules"]:
                v = inv.get("valor_num", 0)
                if v >= rule["min"] and (rule["max"] is None or v <= rule["max"]):
                    base = rule["text"].pt
        out = self.pattern
        for k in ("numero", "fornecedor", "vencimento", "unidade"):
            out = out.replace("{" + k + "}", str(inv.get(k, "")))
        return out.replace("{descricao}", base).upper()

    # ── ticket / Teams previews ──────────────────────────────────────────────
    def tickets_preview(self, sb) -> List[dict]:
        out = []
        for x in self.due_rows(sb, month_key(self.today))["rows"]:
            if x["state"] == "late" and -x["delta"] <= self.tickets["ignore_older_than"]:
                out.append({"supplier": x["name"], "delta": x["delta"], "due": x["due"],
                            "action": "follow_up" if -x["delta"] >= self.tickets["followup_days_after"] else "open"})
            elif x["state"] == "soon" and x["delta"] <= self.tickets["open_days_before"]:
                out.append({"supplier": x["name"], "delta": x["delta"], "due": x["due"], "action": "open"})
        return out

    def teams_preview(self, sb) -> dict:
        ov = self.overview(sb)
        return {"month": ov["month"], "missing": [x["name"] for x in ov["calendar"]["missing"]],
                "missing_total": ov["calendar"]["missing_total"], "paid": ov["calendar"]["counts"]["completed"],
                "queue": ov["in_queue"],
                "returned": sum(1 for e in sb.emails.values() if e.status == wf.READY_FOR_FISCAL)}

    def new_id(self) -> str:
        return uuid.uuid4().hex[:6]


def seed_trash(sb) -> None:
    """Fictional deleted e-mails, so the trash triage and the history have something to show."""
    from .sandbox import Email  # local import: sandbox imports this module

    now = datetime.now().replace(microsecond=0)
    idx = 0
    for cat, (n, senders, subjects) in _TRASH.items():
        for i in range(n):
            ts = now - timedelta(hours=3 + (idx * 4.7) % 700)
            idx += 1
            em = Email(id=f"t{idx:04d}", sender=senders[i % len(senders)],
                       subject=subjects[(i * 7 + idx) % len(subjects)], body="",
                       received_at=ts - timedelta(minutes=20), attachments=[], status=wf.DELETED,
                       category=cat, reason=_REASONS[cat] if (i % 8) not in (0, 1, 2) else "")
            em.timeline.append({"ts": (ts - timedelta(minutes=20)).isoformat(timespec="seconds"),
                                "status": wf.PENDING, "note": T("Received and queued", "Recebido e colocado na fila"),
                                "folder": "Inbox/Fila_Pendente", "read": False})
            em.timeline.append({"ts": ts.isoformat(timespec="seconds"), "status": wf.DELETED,
                                "note": T("Moved to Fila_Excluidos", "Movido para Fila_Excluidos"),
                                "folder": "Fila_Excluidos", "read": True})
            sb.emails[em.id] = em


def seed_logs(sb) -> None:
    """A week of fictional operational logs (login, token refresh, mailbox sync, ticket service, warnings)."""
    now = datetime.now().replace(microsecond=0)
    rows = []

    def add(hours_ago: float, level: str, area: str, who: str, msg: T) -> None:
        rows.append({"ts": (now - timedelta(hours=hours_ago)).isoformat(timespec="seconds"), "level": level,
                     "message": msg, "area": area, "who": who})

    for d in range(7):
        base = d * 24
        for h in (1.5, 3.5, 5.5, 8.5):
            hh = base + h + (d % 3) * 0.3
            add(hh, "INFO", "Mailbox", "system", T("Mailbox sync: no new messages.", "Sincronização da caixa: sem mensagens novas."))
            add(hh + 0.02, "INFO", "Microsoft 365", "system", T("Requesting a new OAuth2 token from Azure AD…",
                                                               "Solicitando novo token OAuth2 ao Azure AD…"))
            add(hh + 0.01, "INFO", "Microsoft 365", "system", T("OAuth2 token obtained. Expires in 59 minutes.",
                                                               "Token OAuth2 obtido com sucesso. Expira em 59 minutos."))
        add(base + 2.2, "INFO", "Login", "anonymous", T(f"Login successful: 'admin.demo' from 203.0.113.{10 + d}.",
                                                       f"Login efetuado: 'admin.demo' de 203.0.113.{10 + d}."))
        add(base + 7.1, "INFO", "Service desk", "system", T("Ticket check (simulation): 2 action(s), 0 failure(s).",
                                                          "Verificação de chamados (simulação): 2 ação(ões), 0 falha(s)."))
        add(base + 6.4, "INFO", "Portal", "system", T("Outlook flag cleared on handled messages.",
                                                    "Marcação do Outlook removida das mensagens tratadas."))
        if d % 2 == 0:
            add(base + 9.0, "WARNING", "Portal", "system", T("A supplier boleto arrived without its invoice; waiting.",
                                                           "Um boleto de fornecedor chegou sem a nota; aguardando."))
        if d == 2:
            add(base + 4.0, "WARNING", "Microsoft 365", "system", T("Graph request slow (4.1 s); no retry needed.",
                                                                  "Requisição ao Graph lenta (4,1 s); sem nova tentativa."))
        if d == 4:
            add(base + 4.6, "ERROR", "Microsoft 365", "system", T("Graph request timed out (attempt 1/3); retried successfully.",
                                                                "Requisição ao Graph expirou (tentativa 1/3); refeita com sucesso."))
    add(26, "INFO", "Server", "system", T("Application startup complete.", "Application startup complete."))
    add(26.01, "INFO", "Server", "system", T("Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)",
                                           "Uvicorn rodando em http://0.0.0.0:8000 (CTRL+C para sair)"))
    rows.sort(key=lambda r: r["ts"], reverse=True)
    sb.logs.extend(rows)

def seed_rules(sb) -> None:
    """Per-supplier routing rules, applied after the history so the past months keep the standard flow."""
    sb.portal.direct_rules.append({
        "id": "d1", "supplier": "AssinaFácil", "dest": "accounts.payable@university.example",
        "how": "forward", "after": "wait_cover",
        "note": T("Protected PDF: only forwarded. Whoever pays sends the cover back.",
                  "PDF protegido: só encaminhado. Quem paga devolve a capa."),
    })
    sb.portal.purchasing_rules.append({
        "id": "p1", "supplier": "Aurora Net Provedor", "to": "purchasing.south@university.example",
        "note": T("The south campus has its own Purchasing desk.", "O campus sul tem um Compras próprio."),
    })

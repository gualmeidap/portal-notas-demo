"""Business logic of the demo, isolated per visitor.

Each visitor gets its own `Sandbox` (in-memory state seeded with two months of
fictional history). On the server, one per browser session; in the static
build (GitHub Pages), the sandbox lives in the visitor's own browser.

User-facing text is always a `T(en, pt)` pair; see `i18n.py`.
"""
from __future__ import annotations

import copy
import io
import threading
import time
import uuid
from collections import Counter, OrderedDict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from . import workflow as wf
from .extraction import DocumentData, Extractor, fold, format_brl, load_rules, parse_brl, parse_date, \
    parse_thread_reply, pdf_to_text
from .i18n import T, tjoin
from .integrations import LocalLLM, MockOCR, MockScraper, MockSharePoint, Outbox
from .pdfgen import render_pdf
from .portal import Portal, categorize, seed_logs, seed_rules, seed_trash
from .samples import (FINANCE_ADDR, Attachment, SampleEmail, manual_samples,
                      newsletter_email, supplier_emails, unknown_vendor_email)

OCR_MIN_CONFIDENCE = 0.80

# Process-wide counters exposed at /metrics (production scrapes these with
# Prometheus and charts them in Grafana).
METRICS: Counter = Counter()
_METRICS_LOCK = threading.Lock()


def count(name: str, n: int = 1) -> None:
    with _METRICS_LOCK:
        METRICS[name] += n


class DemoError(Exception):
    def __init__(self, message: T, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class Email:
    id: str
    sender: str
    subject: str
    body: str
    received_at: datetime
    attachments: List[Attachment]
    status: str = wf.PENDING
    issue: object = ""          # "" or T
    needs_review: bool = False  # extraction ran but a human must confirm the fields
    invoice_ids: List[int] = field(default_factory=list)
    po_number: str = ""
    sharepoint_url: str = ""
    process_type: str = "Automatic"
    timeline: List[dict] = field(default_factory=list)
    vendor_reply: Optional[List[Attachment]] = None
    invoice_requested: bool = False
    cover: Optional[Attachment] = None
    category: str = ""         # trash triage category (set when deleted)
    reason: object = ""        # "" or T: why the e-mail left the queue


class Sandbox:
    def __init__(self, seed: bool = True):
        self.rules = copy.deepcopy(load_rules())
        self.extractor = Extractor(self.rules)
        self.emails: Dict[str, Email] = {}
        self.invoices: Dict[int, dict] = {}
        self.links: Dict[str, List[Attachment]] = {}
        self.incoming: List[SampleEmail] = []
        self.staged: Dict[str, List[Attachment]] = {}
        self.outbox = Outbox()
        self.ocr = MockOCR()
        self.scraper = MockScraper(self.links)
        self.sharepoint = MockSharePoint()
        self.llm = LocalLLM()
        self.logs: deque = deque(maxlen=1500)
        self.monitor = False
        self._clock: Optional[datetime] = None
        self._po_seq = 4700
        self.portal = Portal(date.today())
        if seed:
            _seed(self)

    # ── infrastructure ───────────────────────────────────────────────────────
    def now(self) -> datetime:
        return self._clock or datetime.now().replace(microsecond=0)

    def log(self, level: str, message: T, area: str = "Portal", who: str = "system") -> None:
        self.logs.appendleft({"ts": self.now().isoformat(timespec="seconds"), "level": level, "message": message,
                              "area": area, "who": who})

    def _get(self, email_id: str) -> Email:
        em = self.emails.get(email_id)
        if not em:
            raise DemoError(T("E-mail not found.", "E-mail não encontrado."), 404)
        return em

    def _note(self, em: Email, note: T, status: Optional[str] = None) -> None:
        status = status or em.status
        folder, is_read = wf.mailbox_state(status)
        em.timeline.append({"ts": self.now().isoformat(timespec="seconds"), "status": status, "note": note,
                            "folder": folder, "read": is_read})

    def _set_status(self, em: Email, status: str, note: T) -> None:
        em.status = status
        self._note(em, note, status)

    def add_email(self, sample: SampleEmail, received_at: Optional[datetime] = None) -> Email:
        em = Email(
            id=uuid.uuid4().hex[:10], sender=sample.sender, subject=sample.subject, body=sample.body,
            received_at=received_at or self.now(), attachments=list(sample.attachments),
            vendor_reply=sample.vendor_reply,
        )
        self.links.update(sample.links)
        self.emails[em.id] = em
        em.timeline.append({"ts": em.received_at.isoformat(timespec="seconds"), "status": wf.PENDING,
                            "note": T("Received and queued", "Recebido e colocado na fila"),
                            "folder": "Inbox/Fila_Pendente", "read": False})
        return em

    def addr_purchasing(self) -> str:
        return self.portal.settings["purchasing"]["receives"]

    def addr_fiscal(self) -> str:
        return self.portal.settings["fiscal"]["receives"]

    def _sector_lists(self) -> tuple:
        s = self.portal.settings
        return [s["purchasing"]["receives"], *s["purchasing"]["also"]], [s["fiscal"]["receives"], *s["fiscal"]["also"]]

    def supplier_of_sender(self, sender: str) -> str:
        s = sender.lower()
        for info in self.rules["vendor_map"].values():
            d = info.get("sender_domain")
            if d and s.endswith(d):
                return info["fornecedor"]
        return ""

    def forward_rule(self, em: "Email") -> Optional[dict]:
        name = self.supplier_of_sender(em.sender)
        return next((r for r in self.portal.direct_rules if name and r["how"] == "forward"
                     and r["supplier"].lower() == name.lower()), None)

    def apply_removal_rules(self, em: "Email") -> bool:
        """Senders/subjects listed under 'E-mails outside the system' leave the queue as soon as they arrive."""
        hit = self.portal.matches_removal(em.sender, em.subject)
        if not hit or em.status != wf.PENDING:
            return False
        em.category = categorize(em.sender, em.subject)
        em.reason = T(f"Removed automatically by the rule '{hit}'", f"Removido automaticamente pela regra '{hit}'")
        self._set_status(em, wf.DELETED, T(f"Removed by the rule '{hit}' (moved to Fila_Excluidos)",
                                           f"Removido pela regra '{hit}' (movido para Fila_Excluidos)"))
        self.log("INFO", T(f"Rule '{hit}' removed '{em.subject}' from {em.sender}.",
                           f"A regra '{hit}' removeu '{em.subject}' de {em.sender}."))
        return True

    # ── mailbox ──────────────────────────────────────────────────────────────
    def fetch_inbox(self) -> List[Email]:
        new = [self.add_email(s) for s in self.incoming]
        self.incoming = []
        self.portal.last_sync = self.now()
        for em in new:
            self.apply_removal_rules(em)
        count("emails_ingested_total", len(new))
        if new:
            self.log("INFO", T(f"Mailbox sync (Graph): {len(new)} new message(s) queued as Pending.",
                               f"Sincronização da caixa (Graph): {len(new)} mensagem(ns) nova(s) na fila como Pendente."))
        else:
            self.log("INFO", T("Mailbox sync (Graph): no new messages.",
                               "Sincronização da caixa (Graph): nenhuma mensagem nova."))
        return new

    # ── extraction ───────────────────────────────────────────────────────────
    def _extract_attachment(self, att: Attachment, source: str = "text") -> DocumentData:
        doc = self.extractor.extract_pdf(att.pdf(), att.filename, source)
        if doc.doc_type == "sem_texto" and att.scanned:
            # Same branch as production: no text layer -> OCR.
            doc = self.extractor.extract_text(self.ocr.transcribe(att), att.filename, "ocr")
            conf = att.ocr_confidence
            if conf < OCR_MIN_CONFIDENCE:
                doc.warnings.append(T(f"OCR confidence {conf:.0%} is below {OCR_MIN_CONFIDENCE:.0%}: human review.",
                                      f"Confiança do OCR {conf:.0%} abaixo de {OCR_MIN_CONFIDENCE:.0%}: revisão humana."))
        return doc

    def _documents(self, em: Email) -> List[DocumentData]:
        source = "manual" if em.process_type == "Manual" else "text"
        return [self._extract_attachment(a, source) for a in em.attachments]

    def preview(self, email_id: str) -> dict:
        em = self._get(email_id)
        docs = self._documents(em)
        records, orphans = self.extractor.build_records(docs)
        return {"documents": [d.to_dict() for d in docs], "records": records,
                "orphan_boletos": [d.filename for d in orphans]}

    # ── workflow actions ─────────────────────────────────────────────────────
    def process(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("process", em.status)
        if self.forward_rule(em):
            raise DemoError(T("This supplier is set to be forwarded as it is (Settings › Direct send): use Forward.",
                              "Este fornecedor está configurado para ser encaminhado como está (Configurações › Envio direto): use Encaminhar."), 409)
        started = time.perf_counter()
        em.needs_review = False

        if not em.attachments:
            scraped = self.scraper.try_scrape(em.body)
            if not scraped:
                em.issue = T("No attachment and no known download link: kept in the queue for manual handling.",
                             "Sem anexo e sem link de download conhecido: fica na fila para tratamento manual.")
                self.log("WARNING", T(f"{em.sender}: ", f"{em.sender}: ") + em.issue)
                count("emails_failed_total")
                return {"status": em.status, "message": em.issue}
            em.attachments = scraped
            self._note(em, T(f"No attachment: link scraper downloaded {len(scraped)} file(s) from the supplier portal",
                             f"Sem anexo: o scraper baixou {len(scraped)} arquivo(s) do portal do fornecedor"))
            self.log("INFO", T(f"Link scraper: downloaded {len(scraped)} file(s) for {em.sender}.",
                               f"Scraper de links: {len(scraped)} arquivo(s) baixado(s) de {em.sender}."))
            count("scraper_downloads_total", len(scraped))

        docs = self._documents(em)
        records, orphans = self.extractor.build_records(docs)
        count("documents_read_total", len(docs))
        count("ocr_documents_total", sum(1 for d in docs if d.source == "ocr"))

        if not records:
            if orphans:
                em.issue = T("Only a boleto arrived, the invoice (NF) is missing.",
                             "Chegou só o boleto; falta a nota fiscal.")
                self._set_status(em, wf.MISSING_NF, em.issue)
                self.log("WARNING", T(f"{em.sender}: boleto without invoice. Waiting for the supplier.",
                                      f"{em.sender}: boleto sem nota fiscal. Aguardando o fornecedor."))
                return {"status": em.status, "message": em.issue}
            warnings = sorted({w for d in docs for w in d.warnings})
            em.issue = tjoin("; ", warnings) if warnings else T("No invoice recognized.",
                                                                "Nenhuma nota fiscal reconhecida.")
            self.log("WARNING", T(f"{em.sender}: ", f"{em.sender}: ") + em.issue)
            return {"status": em.status, "message": em.issue}

        warnings = sorted({w for r in records for w in r["warnings"]})
        if warnings:
            em.issue = tjoin(" ", warnings)
            em.needs_review = True
            self.log("WARNING", T(f"{em.sender}: sent to human review. ", f"{em.sender}: enviado para revisão humana. ")
                     + em.issue)
            count("emails_review_total")
            return {"status": em.status, "message": T("Needs review: ", "Precisa de revisão: ") + em.issue}

        self._accept(em, records, note=T("Extracted automatically", "Extraído automaticamente"))
        count("extraction_seconds_total_ms", int((time.perf_counter() - started) * 1000))
        return {"status": em.status, "message": T(f"{len(records)} invoice(s) extracted. Now: {em.status}.",
                                                  f"{len(records)} nota(s) extraída(s). Agora: "
                                                  f"{wf.PRODUCTION_NAMES[em.status]}.")}

    def confirm(self, email_id: str, records: List[dict]) -> dict:
        """Operator-reviewed fields (editable preview) replace the automatic read."""
        em = self._get(email_id)
        wf.check("confirm", em.status)
        clean = [self._validate_record(r) for r in records]
        if not clean:
            raise DemoError(T("Nothing to confirm.", "Nada para confirmar."))
        self._accept(em, clean, note=T("Reviewed and confirmed by the operator", "Revisado e confirmado pelo operador"))
        return {"status": em.status, "message": T(f"Confirmed {len(clean)} invoice(s). Now: {em.status}.",
                                                  f"{len(clean)} nota(s) confirmada(s). Agora: "
                                                  f"{wf.PRODUCTION_NAMES[em.status]}.")}

    def _validate_record(self, r: dict) -> dict:
        errors = []
        for f in ("fornecedor", "unidade", "numero", "valor"):
            if not str(r.get(f, "")).strip():
                errors.append(T(f"'{f}' is required", f"'{f}' é obrigatório"))
        valor_num = parse_brl(str(r.get("valor", "")).replace("R$", "").strip())
        if r.get("valor") and valor_num <= 0:
            errors.append(T("'valor' must look like 1.234,56", "'valor' deve estar no formato 1.234,56"))
        for f in ("emissao", "vencimento"):
            if r.get(f) and not parse_date(r[f]):
                errors.append(T(f"'{f}' must be dd/mm/yyyy", f"'{f}' deve estar em dd/mm/aaaa"))
        if errors:
            raise DemoError(T("Invalid record: ", "Registro inválido: ") + tjoin(", ", errors), 422)
        out = {k: (str(r.get(k, "")).strip()) for k in
               ("fornecedor", "unidade", "cnpj", "numero", "emissao", "vencimento", "competencia", "descricao")}
        out.update(valor=format_brl(valor_num).replace("R$ ", ""), valor_num=valor_num,
                   vendor_key=r.get("vendor_key", ""), direct_to_fiscal=bool(r.get("direct_to_fiscal")),
                   files=r.get("files", []), source=r.get("source", "manual"), warnings=[])
        return out

    def _accept(self, em: Email, records: List[dict], note: T) -> None:
        for r in records:
            inv_id = len(self.invoices) + 1
            self.invoices[inv_id] = {**r, "id": inv_id, "email_id": em.id,
                                     "extracted_at": self.now().isoformat(timespec="seconds")}
            em.invoice_ids.append(inv_id)
        em.issue = ""
        em.needs_review = False
        for r in records:
            self.portal.record_arrival(r["fornecedor"], r.get("vencimento", ""), r["numero"], r["valor_num"],
                                       r.get("emissao", ""), em.id)
        direct = all(r.get("direct_to_fiscal") for r in records)
        rule = next((x for x in self.portal.direct_rules if x["supplier"].lower() == records[0]["fornecedor"].lower()), None)
        buy = next((x for x in self.portal.purchasing_rules
                    if x["supplier"].lower() == records[0]["fornecedor"].lower()), None)
        if rule:  # direct-send rule: the table goes to a person, Purchasing and Fiscal are skipped
            target = wf.DONE if rule["after"] == "close" else wf.AWAITING_COVER
            to, kind = rule["dest"], "fiscal"
        elif direct:
            target, to, kind = wf.AWAITING_FISCAL, self.addr_fiscal(), "fiscal"
        else:
            target, to, kind = wf.AWAITING_PURCHASING, (buy["to"] if buy else self.addr_purchasing()), "purchasing"
        self._set_status(em, target, note + T(f"; forwarded to {to}", f"; encaminhado para {to}"))
        self.outbox.send(self.now(), to, f"ENC: {em.subject}",
                         self._summary_text(em), [a.filename for a in em.attachments], kind=kind)
        count("invoices_extracted_total", len(records))
        count("emails_processed_total")
        self.log("SUCCESS", T(f"{em.sender}: {len(records)} invoice(s) extracted -> {target}.",
                              f"{em.sender}: {len(records)} nota(s) extraída(s) -> {wf.PRODUCTION_NAMES[target]}."))

    def _summary_text(self, em: Email) -> str:
        # E-mails to Purchasing/Fiscal are internal Brazilian documents: Portuguese.
        lines = []
        for i in em.invoice_ids:
            r = self.invoices[i]
            lines.append(f"{r['fornecedor']} | NF {r['numero']} | R$ {r['valor']} | venc. {r['vencimento'] or '-'} "
                         f"| {r['unidade']}")
        return "\n".join(lines)

    def process_queue(self) -> dict:
        pending = [e for e in self.emails.values() if e.status == wf.PENDING and not self.forward_rule(e)]
        moved = 0
        for em in sorted(pending, key=lambda e: e.received_at):
            res = self.process(em.id)
            moved += res["status"] != wf.PENDING
        msg = T(f"{len(pending)} pending e-mail(s) processed, {moved} moved forward.",
                f"{len(pending)} e-mail(s) pendente(s) processado(s), {moved} avançaram.")
        self.log("INFO", T("Queue run: ", "Execução da fila: ") + msg)
        return {"processed": len(pending), "moved": moved, "message": msg}

    def delete(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("delete", em.status)
        em.category = categorize(em.sender, em.subject)
        em.reason = ""
        self._set_status(em, wf.DELETED, T("Deleted by the operator (moved to Fila_Excluidos, marked read)",
                                           "Excluído pelo operador (movido para Fila_Excluidos, marcado como lido)"))
        self.log("INFO", T(f"Deleted: '{em.subject}' from {em.sender}.", f"Excluído: '{em.subject}' de {em.sender}."))
        return {"status": em.status, "message": T("Moved to Fila_Excluidos.", "Movido para Fila_Excluidos.")}

    def restore(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("restore", em.status)
        em.issue = ""
        em.needs_review = False
        self._set_status(em, wf.PENDING, T("Restored (moved back to Fila_Pendente, marked unread)",
                                           "Restaurado (de volta para Fila_Pendente, marcado como não lido)"))
        self.log("INFO", T(f"Restored: '{em.subject}'.", f"Restaurado: '{em.subject}'."))
        return {"status": em.status, "message": T("Back in the processing queue.", "De volta à fila de processamento.")}

    def request_invoice(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("request_invoice", em.status)
        self.outbox.send(self.now(), em.sender, f"RE: {em.subject}",
                         "Olá, recebemos o boleto mas não a nota fiscal. Por favor, responda este e-mail com a NF "
                         "em anexo.", kind="supplier")
        em.invoice_requested = True
        self._note(em, T(f"Missing invoice requested from {em.sender}", f"Nota fiscal solicitada a {em.sender}"))
        self.log("INFO", T(f"Missing-invoice request sent to {em.sender}.",
                           f"Pedido de nota fiscal enviado a {em.sender}."))
        return {"status": em.status, "message": T(f"Request sent to {em.sender}.", f"Pedido enviado a {em.sender}.")}

    def simulate_supplier_reply(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("simulate_supplier_reply", em.status)
        if not em.invoice_requested:
            raise DemoError(T("Request the invoice from the supplier first.",
                              "Peça a nota fiscal ao fornecedor primeiro."), 409)
        reply = parse_thread_reply(em.sender, "Segue a nota fiscal em anexo.", *self._sector_lists())
        self.log("INFO", T(f"Thread reply from {em.sender} classified as '{reply['kind']}' with attachment.",
                           f"Resposta de {em.sender} na thread classificada como '{reply['kind']}', com anexo."))
        em.attachments = em.attachments + list(em.vendor_reply or [])
        em.vendor_reply = None
        em.issue = ""
        self._set_status(em, wf.PENDING, T("Supplier replied with the invoice; back to extraction",
                                           "Fornecedor respondeu com a nota; de volta à extração"))
        return self.process(em.id)

    def simulate_purchasing_reply(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("simulate_purchasing_reply", em.status)
        self._po_seq += 17
        body = f"Bom dia, lançado. PEDIDO: {self._po_seq:06d}"
        reply = parse_thread_reply(self.addr_purchasing(), body, *self._sector_lists())
        em.po_number = reply.get("po_number") or ""
        self._set_status(em, wf.READY_FOR_FISCAL, T(f"Purchasing replied: \"{body}\" -> PO {em.po_number}",
                                                    f"Compras respondeu: \"{body}\" -> pedido {em.po_number}"))
        self.log("SUCCESS", T(f"Purchasing reply parsed: PO {em.po_number} for '{em.subject}'.",
                              f"Resposta do Compras lida: pedido {em.po_number} para '{em.subject}'."))
        return {"status": em.status, "message": T(f"PO {em.po_number} read from the reply.",
                                                  f"Pedido {em.po_number} lido da resposta.")}

    def send_fiscal(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("send_fiscal", em.status)
        fiscal = self.addr_fiscal()
        self.outbox.send(self.now(), fiscal, f"ENC: {em.subject} (pedido {em.po_number})",
                         self._summary_text(em), [a.filename for a in em.attachments], kind="fiscal")
        self._set_status(em, wf.AWAITING_FISCAL, T(f"Forwarded to {fiscal} with PO {em.po_number}",
                                                   f"Encaminhado para {fiscal} com o pedido {em.po_number}"))
        self.log("INFO", T(f"Sent to Fiscal: '{em.subject}'.", f"Enviado ao Fiscal: '{em.subject}'."))
        return {"status": em.status, "message": T("Forwarded to Fiscal.", "Encaminhado ao Fiscal.")}

    def simulate_fiscal_reply(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("simulate_fiscal_reply", em.status)
        body = "FISCAL OK - documento lançado. Capa em anexo."
        reply = parse_thread_reply(self.addr_fiscal(), body, *self._sector_lists())
        assert reply["kind"] == "fiscal"
        em.cover = Attachment("Capa_Fiscal.pdf", self._cover_lines(em))
        supplier = self.invoices[em.invoice_ids[0]]["fornecedor"] if em.invoice_ids else "Unknown"
        em.sharepoint_url = self.sharepoint.upload_package(supplier, self.now(), [a.filename for a in em.attachments])
        self._set_status(em, wf.READY_TO_PRINT,
                         T("Fiscal replied \"FISCAL OK\" with the cover; invoice + boleto archived to SharePoint",
                           "Fiscal respondeu \"FISCAL OK\" com a capa; nota + boleto arquivados no SharePoint"))
        count("sharepoint_uploads_total")
        self.log("SUCCESS", T(f"Archived to SharePoint: {em.sharepoint_url}",
                              f"Arquivado no SharePoint: {em.sharepoint_url}"))
        return {"status": em.status, "message": T("Fiscal OK. Package archived to SharePoint.",
                                                  "Fiscal OK. Pacote arquivado no SharePoint.")}

    def finalize(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("finalize", em.status)
        self._set_status(em, wf.DONE, T("Package printed and closed", "Pacote impresso e finalizado"))
        self.log("SUCCESS", T(f"Completed: '{em.subject}'.", f"Concluído: '{em.subject}'."))
        return {"status": em.status, "message": T("Completed.", "Concluído.")}

    def forward(self, email_id: str) -> dict:
        """Direct-send supplier whose PDF is protected: the e-mail goes on as it is, without reading the PDF."""
        em = self._get(email_id)
        wf.check("forward", em.status)
        rule = self.forward_rule(em)
        if not rule:
            raise DemoError(T("There is no direct-send rule for this sender.",
                              "Não há regra de envio direto para este remetente."), 409)
        self.outbox.send(self.now(), rule["dest"], f"ENC: {em.subject}", "", [a.filename for a in em.attachments],
                         kind="fiscal")
        self.portal.record_arrival(rule["supplier"], "", "-", 0.0, "", em.id)
        target = wf.DONE if rule["after"] == "close" else wf.AWAITING_COVER
        self._set_status(em, target, T(f"Forwarded as it is to {rule['dest']} (direct-send rule, PDF not read)",
                                       f"Encaminhado como está para {rule['dest']} (regra de envio direto, PDF não lido)"))
        self.log("INFO", T(f"Forwarded '{em.subject}' to {rule['dest']}.", f"'{em.subject}' encaminhado para {rule['dest']}."))
        return {"status": em.status, "message": T(f"Forwarded to {rule['dest']}.", f"Encaminhado para {rule['dest']}.")}

    def simulate_cover_reply(self, email_id: str) -> dict:
        em = self._get(email_id)
        wf.check("simulate_cover_reply", em.status)
        rule = self.forward_rule(em) or {}
        em.cover = Attachment("Capa_Pagamento.pdf", self._cover_lines(em))
        em.sharepoint_url = self.sharepoint.upload_package(rule.get("supplier") or "Direct send", self.now(),
                                                           [a.filename for a in em.attachments])
        self._set_status(em, wf.READY_TO_PRINT, T("The person who pays sent the cover back; package archived to SharePoint",
                                                  "Quem paga devolveu a capa; pacote arquivado no SharePoint"))
        count("sharepoint_uploads_total")
        return {"status": em.status, "message": T("Cover received. Ready to print.", "Capa recebida. Pronto para impressão.")}

    ACTIONS = ("process", "forward", "delete", "restore", "request_invoice", "simulate_supplier_reply",
               "simulate_purchasing_reply", "send_fiscal", "simulate_fiscal_reply", "simulate_cover_reply", "finalize")

    def run_action(self, email_id: str, action: str) -> dict:
        if action not in self.ACTIONS:
            raise DemoError(T(f"Unknown action '{action}'.", f"Ação desconhecida '{action}'."), 404)
        return getattr(self, action)(email_id)

    def _cover_lines(self, em: Email) -> List[str]:
        lines = ["CAPA FISCAL - DOCUMENTO DE ENTRADA", "", f"Recebido em: {em.received_at:%d/%m/%Y}",
                 f"Pedido de compra: {em.po_number or '-'}", ""]
        for i in em.invoice_ids:
            r = self.invoices[i]
            lines += [f"Fornecedor: {r['fornecedor']}", f"Unidade: {r['unidade']}", f"NF: {r['numero']}",
                      f"Valor: R$ {r['valor']}", f"Vencimento: {r['vencimento'] or '-'}", ""]
        lines.append("Lançado pelo setor Fiscal (documento fictício de demonstração)")
        return lines

    def package_pdf(self, email_id: str) -> bytes:
        """Cover + invoice + boleto in one PDF, ready to print (production does the same)."""
        from pypdf import PdfReader, PdfWriter

        em = self._get(email_id)
        if not em.cover:
            raise DemoError(T("The package exists after Fiscal replies.", "O pacote existe depois que o Fiscal responde."),
                            409)
        writer = PdfWriter()
        for att in [em.cover] + em.attachments:
            pdf = att.pdf() if not att.scanned else render_pdf(["[pagina digitalizada - transcricao do OCR]", ""] +
                                                               att.ocr_text.splitlines())
            for page in PdfReader(io.BytesIO(pdf)).pages:
                writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

    # ── manual upload with editable preview ──────────────────────────────────
    def manual_preview(self, files: List[tuple]) -> dict:
        if not files:
            raise DemoError(T("Send at least one PDF.", "Envie pelo menos um PDF."))
        atts = []
        for name, data in files:
            if not name.lower().endswith(".pdf"):
                raise DemoError(T(f"{name}: only PDF files are accepted.", f"{name}: só arquivos PDF são aceitos."), 415)
            if len(data) > 5 * 1024 * 1024:
                raise DemoError(T(f"{name}: file larger than 5 MB.", f"{name}: arquivo maior que 5 MB."), 413)
            atts.append(Attachment(name, data=data))
        docs = [self.extractor.extract_pdf(a.data, a.filename, "manual") for a in atts]
        records, orphans = self.extractor.build_records(docs)
        token = uuid.uuid4().hex[:12]
        self.staged[token] = atts
        if len(self.staged) > 20:
            self.staged.pop(next(iter(self.staged)))
        return {"token": token, "documents": [d.to_dict() for d in docs], "records": records,
                "orphan_boletos": [d.filename for d in orphans]}

    def manual_confirm(self, token: str, records: List[dict], destination: str) -> dict:
        atts = self.staged.pop(token, None)
        if atts is None:
            raise DemoError(T("Preview expired. Upload the files again.", "A prévia expirou. Envie os arquivos de novo."),
                            410)
        if destination not in ("purchasing", "fiscal"):
            raise DemoError(T("Destination must be 'purchasing' or 'fiscal'.",
                              "O destino deve ser 'purchasing' ou 'fiscal'."))
        for r in records:
            r["direct_to_fiscal"] = destination == "fiscal"
        clean = [self._validate_record(r) for r in records]
        if not clean:
            raise DemoError(T("Nothing to confirm.", "Nada para confirmar."))
        em = Email(id=uuid.uuid4().hex[:10], sender="Upload manual", subject="Upload manual: "
                   f"{', '.join(a.filename for a in atts)}", body="", received_at=self.now(), attachments=atts,
                   process_type="Manual")
        em.timeline.append({"ts": self.now().isoformat(timespec="seconds"), "status": wf.PENDING,
                            "note": T("Uploaded by the operator", "Enviado pelo operador"), "folder": "-",
                            "read": True})
        self.emails[em.id] = em
        self._accept(em, clean, note=T("Manual upload reviewed by the operator", "Upload manual revisado pelo operador"))
        return {"status": em.status, "email_id": em.id,
                "message": T(f"{len(clean)} invoice(s) created. Now: {em.status}.",
                             f"{len(clean)} nota(s) criada(s). Agora: {wf.PRODUCTION_NAMES[em.status]}.")}

    # ── suppliers ────────────────────────────────────────────────────────────
    def vendors(self) -> List[dict]:
        out = []
        for key, info in sorted(self.rules["vendor_map"].items()):
            invs = [i for i in self.invoices.values() if i.get("vendor_key") == key]
            out.append({"key": key, **info, "invoices": len(invs),
                        "total": format_brl(sum(i["valor_num"] for i in invs))})
        return out

    def upsert_vendor(self, key: str, data: dict) -> dict:
        key = fold(key).upper().strip()
        if len(key) < 3:
            raise DemoError(T("The key must have at least 3 characters (it is searched in the PDF text).",
                              "A chave precisa de pelo menos 3 caracteres (ela é procurada no texto do PDF)."), 422)
        if not str(data.get("fornecedor", "")).strip() or not str(data.get("unidade", "")).strip():
            raise DemoError(T("Supplier name and unit are required.", "Nome do fornecedor e unidade são obrigatórios."),
                            422)
        self.rules["vendor_map"][key] = {
            "fornecedor": data["fornecedor"].strip(), "unidade": data["unidade"].strip(),
            "cnpj": (data.get("cnpj") or "").strip(), "sender_domain": (data.get("sender_domain") or "").strip(),
            "direct_to_fiscal": bool(data.get("direct_to_fiscal")),
        }
        self.extractor = Extractor(self.rules)
        self.log("INFO", T(f"Supplier rule saved: {key} -> {data['fornecedor']}.",
                           f"Regra de fornecedor salva: {key} -> {data['fornecedor']}."))
        return {"key": key, **self.rules["vendor_map"][key]}

    def delete_vendor(self, key: str) -> None:
        if self.rules["vendor_map"].pop(key, None) is None:
            raise DemoError(T("Supplier not found.", "Fornecedor não encontrado."), 404)
        self.extractor = Extractor(self.rules)
        self.log("INFO", T(f"Supplier rule removed: {key}.", f"Regra de fornecedor removida: {key}."))

    def ai_vendor(self, pdf: Optional[bytes] = None, email_id: Optional[str] = None) -> dict:
        if email_id:
            em = self._get(email_id)
            atts = [a for a in em.attachments if "boleto" not in a.filename.lower()] or em.attachments
            if not atts:
                raise DemoError(T("This e-mail has no attachment to read.", "Este e-mail não tem anexo para ler."))
            text = self.ocr.transcribe(atts[0]) if atts[0].scanned else pdf_to_text(atts[0].pdf())
        elif pdf:
            text = pdf_to_text(pdf)
        else:
            raise DemoError(T("Send a PDF or an e-mail id.", "Envie um PDF ou o id de um e-mail."))
        if not text.strip():
            raise DemoError(T("The PDF has no text layer (production would OCR it first).",
                              "O PDF não tem camada de texto (em produção passaria pelo OCR antes)."), 422)
        try:
            result = self.llm.extract_vendor(text)
        except Exception as exc:
            raise DemoError(T(f"LLM call failed: {exc}", f"A chamada ao LLM falhou: {exc}"), 502)
        count("llm_calls_total")
        self.log("INFO", T(f"LLM ({self.llm.mode}) suggested supplier '{result.get('chave_normalizada')}'.",
                           f"LLM ({self.llm.mode}) sugeriu o fornecedor '{result.get('chave_normalizada')}'."))
        return {"mode": self.llm.mode, "suggestion": result}

    # ── finance ──────────────────────────────────────────────────────────────
    def invoice_rows(self) -> List[dict]:
        rows = []
        for inv in sorted(self.invoices.values(), key=lambda i: i["extracted_at"], reverse=True):
            em = self.emails[inv["email_id"]]
            if em.status == wf.DELETED:
                continue
            at = {t["status"]: t["ts"] for t in reversed(em.timeline)}
            rows.append({**inv, "status": em.status, "po_number": em.po_number, "sharepoint_url": em.sharepoint_url,
                         "process_type": em.process_type, "sender": em.sender, "description": self.portal.describe(inv),
                         "purchasing_at": at.get(wf.READY_FOR_FISCAL, ""), "fiscal_at": at.get(wf.READY_TO_PRINT, "")})
        return rows

    def finance_xlsx(self) -> bytes:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "Notas Fiscais"
        headers = ["Unidade", "Fornecedor", "CNPJ", "NF", "Emissão", "Vencimento", "Valor (R$)", "Descrição",
                   "Pedido", "Status"]
        ws.append(headers)
        for r in self.invoice_rows():
            ws.append([r["unidade"], r["fornecedor"], r["cnpj"], r["numero"], r["emissao"], r["vencimento"],
                       r["valor_num"], r["descricao"], r["po_number"], wf.PRODUCTION_NAMES[r["status"]]])
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F3A5F")
            cell.alignment = Alignment(horizontal="center")
        for row in ws.iter_rows(min_row=2, min_col=7, max_col=7):
            for cell in row:
                cell.number_format = '#,##0.00'
        widths = [16, 24, 20, 10, 12, 12, 13, 48, 10, 22]
        for i, w in enumerate(widths):
            ws.column_dimensions[chr(65 + i)].width = w
        ws.freeze_panes = "A2"
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()

    def send_finance_report(self) -> dict:
        rows = self.invoice_rows()
        total = sum(r["valor_num"] for r in rows)
        self.outbox.send(self.now(), FINANCE_ADDR, f"Notas fiscais de fornecedores - planilha consolidada ({len(rows)} NF)",
                         f"Em anexo: {len(rows)} nota(s), total {format_brl(total)}.",
                         ["notas_fiscais.xlsx"], kind="finance")
        count("finance_reports_total")
        self.log("SUCCESS", T(f"Spreadsheet sent to Finance: {len(rows)} invoice(s), {format_brl(total)}.",
                              f"Planilha enviada ao Financeiro: {len(rows)} nota(s), {format_brl(total)}."))
        return {"message": T(f"Spreadsheet with {len(rows)} invoice(s) sent to {FINANCE_ADDR}.",
                             f"Planilha com {len(rows)} nota(s) enviada para {FINANCE_ADDR}.")}

    # ── read models ──────────────────────────────────────────────────────────
    def email_view(self, em: Email, full: bool = False) -> dict:
        folder, is_read = wf.mailbox_state(em.status)
        invs = [self.invoices[i] for i in em.invoice_ids]
        out = {
            "id": em.id, "sender": em.sender, "subject": em.subject, "received_at": em.received_at.isoformat(),
            "status": em.status, "status_pt": wf.PRODUCTION_NAMES[em.status], "issue": em.issue,
            "needs_review": em.needs_review,
            "unknown_supplier": isinstance(em.issue, T) and "rules file" in em.issue.en,
            "attachments": [{"filename": a.filename, "scanned": a.scanned} for a in em.attachments],
            "has_link": bool(not em.attachments and "https://" in em.body),
            "folder": folder, "read": is_read, "po_number": em.po_number, "sharepoint_url": em.sharepoint_url,
            "process_type": em.process_type, "invoice_requested": em.invoice_requested,
            "has_package": em.cover is not None, "manual": em.process_type == "Manual",
            "attach_count": len(em.attachments), "bulk": len(em.invoice_ids) > 1 or len(em.attachments) > 2,
            "can_forward": em.status == wf.PENDING and self.forward_rule(em) is not None,
            "supplier": invs[0]["fornecedor"] if invs else "",
            "total": format_brl(sum(i["valor_num"] for i in invs)) if invs else "",
            "updated_at": em.timeline[-1]["ts"] if em.timeline else em.received_at.isoformat(),
        }
        if full:
            out.update(body=em.body, timeline=em.timeline, invoices=invs)
        return out

    def list_emails(self, view: str) -> List[dict]:
        groups = {"queue": wf.QUEUE, "workflow": wf.BOARD, "open": wf.QUEUE + wf.BOARD, "history": wf.CLOSED,
                  "all": tuple(wf.PRODUCTION_NAMES)}
        if view not in groups:
            raise DemoError(T("view must be queue, workflow, history or all.",
                              "view deve ser queue, workflow, history ou all."))
        items = [e for e in self.emails.values() if e.status in groups[view]]
        items.sort(key=lambda e: e.timeline[-1]["ts"] if e.timeline else "", reverse=True)
        return [self.email_view(e) for e in items]

    def email_detail(self, email_id: str) -> dict:
        return self.email_view(self._get(email_id), full=True)

    def attachment(self, email_id: str, name: str) -> Attachment:
        em = self._get(email_id)
        for a in em.attachments + ([em.cover] if em.cover else []):
            if a.filename == name:
                return a
        raise DemoError(T("Attachment not found.", "Anexo não encontrado."), 404)

    def summary(self) -> dict:
        by_status = Counter(e.status for e in self.emails.values())
        rows = self.invoice_rows()
        month = self.now().strftime("%Y-%m")
        month_rows = [r for r in rows if r["extracted_at"][:7] == month]
        return {
            "by_status": {s: by_status.get(s, 0) for s in wf.PRODUCTION_NAMES},
            "queue": sum(by_status.get(s, 0) for s in wf.QUEUE),
            "in_workflow": sum(by_status.get(s, 0) for s in wf.BOARD),
            "invoices_total": len(rows),
            "invoices_month": len(month_rows),
            "amount_month": format_brl(sum(r["valor_num"] for r in month_rows)),
            "suppliers": len(self.rules["vendor_map"]),
            "incoming": len(self.incoming),
            "monitor": self.monitor,
            "llm_mode": self.llm.mode,
            "by_supplier": self._by_supplier(rows),
        }

    def _by_supplier(self, rows: List[dict]) -> List[dict]:
        agg: Dict[str, dict] = {}
        for r in rows:
            a = agg.setdefault(r["fornecedor"], {"fornecedor": r["fornecedor"], "count": 0, "total_num": 0.0})
            a["count"] += 1
            a["total_num"] += r["valor_num"]
        out = sorted(agg.values(), key=lambda a: a["total_num"], reverse=True)
        for a in out:
            a["total"] = format_brl(a["total_num"])
        return out

    def samples(self) -> Dict[str, bytes]:
        return {name: render_pdf(lines) for name, lines in manual_samples(self.now().date()).items()}


# ── seed: two months of history + the current month in flight ────────────────
def _seed(sb: Sandbox) -> None:
    today = date.today()

    def at(d: date, hour: float) -> datetime:
        return datetime.combine(d, datetime.min.time()) + timedelta(hours=hour)

    def run_full(em: Email, start: datetime) -> None:
        sb._clock = start + timedelta(minutes=20)
        sb.process(em.id)
        if em.status == wf.PENDING:  # review path: operator confirms the preview
            sb.confirm(em.id, sb.preview(em.id)["records"])
        if em.status == wf.MISSING_NF:
            sb.request_invoice(em.id)
            sb._clock += timedelta(days=1)
            sb.simulate_supplier_reply(em.id)
        steps = [(wf.AWAITING_PURCHASING, sb.simulate_purchasing_reply, 1),
                 (wf.READY_FOR_FISCAL, sb.send_fiscal, 0.1),
                 (wf.AWAITING_FISCAL, sb.simulate_fiscal_reply, 2),
                 (wf.READY_TO_PRINT, sb.finalize, 0.5)]
        for status, fn, days in steps:
            if em.status == status:
                sb._clock += timedelta(days=days)
                fn(em.id)

    # History: the two previous months, every supplier completed.
    for offset in (2, 1):
        first = date(today.year, today.month, 1)
        for _ in range(offset):
            first = (first - timedelta(days=1)).replace(day=1)
        for i, sample in enumerate(supplier_emails(today, month_offset=offset, seq=offset).values()):
            received = at(first + timedelta(days=2 + i % 4), 8 + i)
            sb._clock = received
            em = sb.add_email(sample, received)
            run_full(em, received)
        spam = sb.add_email(newsletter_email(), at(first + timedelta(days=5), 10))
        sb._clock = spam.received_at + timedelta(hours=1)
        sb.delete(spam.id)

    # Current month: a few e-mails already moving through the workflow…
    cur = supplier_emails(today, month_offset=0, seq=0)
    now = datetime.now().replace(microsecond=0)

    def place(key: str, hours_ago: float, until: str) -> None:
        received = now - timedelta(hours=hours_ago)
        sb._clock = received
        em = sb.add_email(cur[key], received)
        sb._clock = received + timedelta(minutes=15)
        sb.process(em.id)
        chain = [(wf.AWAITING_PURCHASING, sb.simulate_purchasing_reply),
                 (wf.READY_FOR_FISCAL, sb.send_fiscal),
                 (wf.AWAITING_FISCAL, sb.simulate_fiscal_reply)]
        for status, fn in chain:
            if em.status == until:
                break
            if em.status == status:
                sb._clock += timedelta(hours=hours_ago / 4)
                fn(em.id)

    place("FIBRANORTE", 30, wf.AWAITING_PURCHASING)
    place("VALELINK", 70, wf.READY_FOR_FISCAL)
    place("NUVEMCERTA", 50, wf.AWAITING_FISCAL)
    place("NOMERAIZ DOMINIOS", 90, wf.READY_TO_PRINT)

    # …and some still waiting in the queue.
    for key, hours in (("AURORA NET", 5), ("ASSINAFACIL", 3), ("PONTOCOM FIBRA", 2)):
        sb.add_email(cur[key], now - timedelta(hours=hours))
    sb.add_email(newsletter_email(), now - timedelta(hours=1))

    # Arrive when the visitor clicks "Check inbox".
    scanned = cur["SINALMAX"]
    scanned.attachments[0].ocr_confidence = 0.71  # low-confidence read -> human review
    sb.incoming = [scanned, unknown_vendor_email(today)]

    sb._clock = None
    seed_trash(sb)
    seed_rules(sb)
    sb.logs.clear()
    sb.outbox.messages = sb.outbox.messages[:12]
    sb.log("SUCCESS", T("Demo sandbox ready: in-memory data, fictional suppliers, mocked Microsoft 365.",
                        "Sandbox da demo pronta: dados em memória, fornecedores fictícios, Microsoft 365 simulado."))
    seed_logs(sb)


class SandboxManager:
    """One sandbox per browser session, evicted after inactivity (LRU)."""

    def __init__(self, factory=Sandbox, max_sessions: int = 300, ttl_seconds: int = 3 * 3600):
        self.factory = factory
        self.max_sessions = max_sessions
        self.ttl = ttl_seconds
        self._items: "OrderedDict[str, tuple]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, sid: str) -> Sandbox:
        now = time.monotonic()
        with self._lock:
            for key in [k for k, (_, seen) in self._items.items() if now - seen > self.ttl]:
                del self._items[key]
            if sid in self._items:
                sb, _ = self._items.pop(sid)
            else:
                sb = self.factory()
                count("sandboxes_created_total")
            self._items[sid] = (sb, now)
            while len(self._items) > self.max_sessions:
                self._items.popitem(last=False)
            return sb

    def reset(self, sid: str) -> Sandbox:
        with self._lock:
            self._items.pop(sid, None)
        return self.get(sid)

    def __len__(self) -> int:
        return len(self._items)

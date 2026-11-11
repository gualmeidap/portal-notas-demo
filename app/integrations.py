"""Mock integrations.

Production talks to Microsoft Graph (mailbox), SharePoint, SMTP, Tesseract OCR,
a local LLM (Ollama) and a few supplier portals. The demo replaces each one
with an in-memory stand-in that keeps the same contract, so the business logic
above them is the code being shown, not the mocks.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote

import urllib.request

from .samples import Attachment

LINK_RE = re.compile(r"https://(?:portal|faturas)\.[a-z0-9-]+\.example/\S+")


class MockOCR:
    """Production: Tesseract over each page image. Demo: the scanned sample
    documents carry their transcription, so only the branch is exercised."""

    def transcribe(self, att: Attachment) -> str:
        return att.ocr_text or ""


class MockScraper:
    """Some suppliers never attach the PDF, they send a download link. Production
    has one small scraper per supplier portal; the demo resolves links against
    a registry of fictional URLs."""

    def __init__(self, registry: Dict[str, List[Attachment]]):
        self.registry = registry

    def try_scrape(self, body: str) -> List[Attachment]:
        for url in LINK_RE.findall(body or ""):
            url = url.rstrip(".,;")
            if url in self.registry:
                return list(self.registry[url])
        return []


class MockSharePoint:
    """Archives the invoice package in a dated folder per supplier."""

    BASE = "https://tenant.sharepoint.example/sites/Fiscal/Shared%20Documents"

    def upload_package(self, supplier: str, when: datetime, filenames: List[str]) -> str:
        safe = re.sub(r"[^\w\- ]", "", unicodedata.normalize("NFKD", supplier)).strip() or "Unknown"
        return f"{self.BASE}/{when:%Y}/{when:%m}/{quote(safe)}"


LLM_PROMPT = """You are an assistant specialized in Brazilian fiscal documents.
Extract the supplier (issuer) from the text below and return STRICTLY a JSON object with:
- "razao_social": full legal name
- "nome_fantasia": trade name (or the legal name if none)
- "chave_normalizada": UPPERCASE key with no legal suffixes (LTDA, S.A., EIRELI), e.g. "FIBRANORTE"
- "unidade": city or branch mentioned, or ""

DOCUMENT TEXT:
{text}"""


class LocalLLM:
    """Registers a new supplier from one of its PDFs.

    Production calls a model served by Ollama on the local network (documents
    never leave the company). Set OLLAMA_URL / OLLAMA_MODEL to do the same
    here; without them a deterministic heuristic returns the same JSON shape.
    """

    SUFFIXES = re.compile(r"\b(LTDA|S\.?A\.?|EIRELI|ME|EPP|SERVICOS|SERVIÇOS)\b\.?", re.IGNORECASE)

    def __init__(self):
        self.url = os.getenv("OLLAMA_URL")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    @property
    def mode(self) -> str:
        return "ollama" if self.url else "mock"

    def extract_vendor(self, text: str) -> dict:
        if self.url:
            return self._ollama(text)
        return self._heuristic(text)

    def _ollama(self, text: str) -> dict:
        payload = json.dumps({
            "model": self.model, "stream": False, "format": "json",
            "messages": [{"role": "user", "content": LLM_PROMPT.format(text=text[:2500])}],
        }).encode()
        req = urllib.request.Request(self.url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (URL set by the operator)
            data = json.loads(resp.read())
        content = (data.get("message") or {}).get("content", "").strip().strip("`")
        if content.startswith("json"):
            content = content[4:]
        return json.loads(content)

    def _heuristic(self, text: str) -> dict:
        razao = ""
        m = re.search(r"Raz[ãa]o Social:\s*(.+)", text)
        if m:
            razao = m.group(1).strip()
        else:
            m = re.search(r"Benefici[áa]rio:\s*([^-\n]+)", text)
            razao = m.group(1).strip() if m else ""
        fantasia = self.SUFFIXES.sub("", razao).strip(" -.,").title()
        chave = unicodedata.normalize("NFKD", fantasia).encode("ascii", "ignore").decode().upper()
        chave = re.sub(r"[^A-Z0-9 ]", "", chave).strip()
        cidade = ""
        m = re.search(r"Munic[íi]pio:\s*([^/\n]+)", text)
        if m:
            cidade = m.group(1).strip().title()
        return {"razao_social": razao, "nome_fantasia": fantasia, "chave_normalizada": chave, "unidade": cidade}


class Outbox:
    """Stand-in for SMTP / Graph sendMail. Every message the system would send
    is recorded so the visitor can see who gets what, and when."""

    def __init__(self):
        self.messages: List[dict] = []

    def send(self, when: datetime, to: str, subject: str, body: str,
             attachments: Optional[List[str]] = None, kind: str = "") -> dict:
        msg = {
            "id": len(self.messages) + 1, "ts": when.isoformat(timespec="seconds"), "to": to,
            "subject": subject, "body": body, "attachments": attachments or [], "kind": kind,
        }
        self.messages.insert(0, msg)
        return msg

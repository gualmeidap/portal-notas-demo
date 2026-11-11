"""Invoice extraction engine.

Mirrors the production pipeline:

    PDF bytes -> text (pypdf; OCR fallback) -> classify (boleto / NF / both)
    -> supplier lookup (rules file, then CNPJ, then "razão social" fallback)
    -> field extraction (regex rules) -> NF-first records (NF paired with its
    boleto by amount)

Production differences, kept explicit:
* OCR: production runs Tesseract on scanned PDFs. The public demo has no OCR
  engine, so "scanned" sample documents ship their OCR text pre-computed and
  are flagged `source="ocr"`. Uploaded image-only PDFs are reported as such.
* Rules are fictional, but the file has the same shape as the real one.
"""
from __future__ import annotations

import io
import json
import re
import unicodedata
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .i18n import T

RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "vendor_rules.json"

REQUIRED_FIELDS = ("fornecedor", "numero", "valor")


def load_rules(path: Path = RULES_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def fold(text: str) -> str:
    """Lowercase and strip accents while keeping a 1:1 character mapping.

    Matching happens on the folded text, but captured spans are read back from
    the original, so "Serviços" is matched as "servicos" and returned intact.
    """
    out = []
    for ch in text:
        base = unicodedata.normalize("NFKD", ch)
        out.append((base[0] if base else ch).lower())
    return "".join(out)


def parse_brl(value: str) -> float:
    """'1.890,00' -> 1890.0"""
    try:
        return float(value.replace(".", "").replace(",", "."))
    except (AttributeError, ValueError):
        return 0.0


def format_brl(value: float) -> str:
    whole, cents = f"{value:,.2f}".split(".")
    return f"R$ {whole.replace(',', '.')},{cents}"


def parse_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


@dataclass
class DocumentData:
    """Unified structure for any fiscal document (same idea as production)."""

    filename: str = ""
    doc_type: str = "desconhecido"  # boleto | nota_fiscal | combinado | desconhecido | sem_texto
    source: str = "text"  # text | ocr | scraper | manual
    fornecedor: str = ""
    vendor_key: str = ""
    unidade: str = ""
    cnpj: str = ""
    numero: str = ""
    emissao: str = ""
    vencimento: str = ""
    competencia: str = ""
    descricao: str = ""
    valor: str = ""
    valor_num: float = 0.0
    direct_to_fiscal: bool = False
    warnings: List[T] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {f.name: (list(getattr(self, f.name)) if f.name == "warnings" else getattr(self, f.name))
                for f in fields(self)}


def pdf_to_text(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader  # imported lazily: only needed for real PDFs

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


class Extractor:
    def __init__(self, rules: Optional[dict] = None):
        self.rules = rules or load_rules()
        self.patterns = {k: re.compile(v, re.IGNORECASE) for k, v in self.rules["regex_patterns"].items()}
        self.boleto_kw = [fold(k) for k in self.rules["boleto_kw"]]
        self.nf_kw = [fold(k) for k in self.rules["nf_kw"]]

    # ── helpers ──────────────────────────────────────────────────────────────
    def _find(self, name: str, text: str, folded: str) -> str:
        m = self.patterns[name].search(folded)
        if not m:
            return ""
        return text[m.start(1):m.end(1)].strip()

    def classify(self, folded: str) -> str:
        b = sum(1 for kw in self.boleto_kw if kw in folded)
        n = sum(1 for kw in self.nf_kw if kw in folded)
        if n >= 2 and b >= 3:
            return "combinado"
        if n >= 2:
            return "nota_fiscal"
        if b >= 2:
            return "boleto"
        return "desconhecido"

    def lookup_vendor(self, folded: str, cnpjs: List[str]) -> Tuple[str, Optional[dict]]:
        squashed = folded.replace(" ", "")
        vendor_map: Dict[str, dict] = self.rules["vendor_map"]
        for key, info in vendor_map.items():
            k = fold(key)
            if k in folded or k.replace(" ", "") in squashed:
                return key, info
        for key, info in vendor_map.items():
            if info.get("cnpj") and info["cnpj"] in cnpjs:
                return key, info
        return "", None

    def _valor(self, text: str, folded: str) -> Tuple[str, float]:
        labeled = self._find("valor_rotulado", text, folded)
        if labeled:
            return labeled, parse_brl(labeled)
        # Fallback: the largest amount on the page is usually the total.
        amounts = [m.group(1) for m in self.patterns["valor_qualquer"].finditer(folded)]
        if not amounts:
            return "", 0.0
        best = max(amounts, key=parse_brl)
        return best, parse_brl(best)

    # ── entry point ──────────────────────────────────────────────────────────
    def extract_text(self, text: str, filename: str = "", source: str = "text") -> DocumentData:
        doc = DocumentData(filename=filename, source=source)
        if not text.strip():
            doc.doc_type = "sem_texto"
            doc.warnings.append(T(
                "No text layer: this looks like a scanned image. Production sends it to OCR "
                "(Tesseract); the public demo has no OCR engine.",
                "Sem camada de texto: parece uma imagem digitalizada. Em produção vai para o OCR "
                "(Tesseract); a demo pública não tem motor de OCR.",
            ))
            return doc

        folded = fold(text)
        doc.doc_type = self.classify(folded)
        cnpjs = [m.group(1) for m in self.patterns["cnpj"].finditer(text)]
        doc.cnpj = cnpjs[0] if cnpjs else ""

        key, info = self.lookup_vendor(folded, cnpjs)
        if info:
            doc.vendor_key = key
            doc.fornecedor = info["fornecedor"]
            doc.unidade = info.get("unidade", "")
            doc.direct_to_fiscal = bool(info.get("direct_to_fiscal"))
            doc.cnpj = info.get("cnpj") or doc.cnpj
        else:
            fallback = self._find("razao_social", text, folded)
            doc.fornecedor = fallback.split("  ")[0].strip()[:60]
            doc.warnings.append(T("Supplier not in the rules file: needs review before it moves on.",
                                  "Fornecedor fora do arquivo de regras: precisa de revisão antes de seguir."))

        doc.numero = self._find("numero", text, folded) if doc.doc_type in ("nota_fiscal", "combinado") else ""
        doc.emissao = self._find("emissao", text, folded)
        doc.vencimento = self._find("vencimento", text, folded)
        doc.competencia = self._find("competencia", text, folded)
        doc.descricao = self._find("descricao", text, folded)[:120]
        doc.valor, doc.valor_num = self._valor(text, folded)

        if doc.doc_type in ("nota_fiscal", "combinado"):
            for f in REQUIRED_FIELDS:
                if not getattr(doc, f):
                    doc.warnings.append(T(f"Could not read '{f}': goes to human review instead of being guessed.",
                                          f"Não foi possível ler '{f}': vai para revisão humana em vez de ser chutado."))
        if doc.doc_type == "desconhecido":
            doc.warnings.append(T("Unrecognized template: neither boleto nor invoice keywords matched.",
                                  "Modelo não reconhecido: nenhuma palavra-chave de boleto ou de nota fiscal."))
        return doc

    def extract_pdf(self, pdf_bytes: bytes, filename: str = "", source: str = "text") -> DocumentData:
        try:
            text = pdf_to_text(pdf_bytes)
        except Exception as exc:  # corrupted or encrypted PDF
            doc = DocumentData(filename=filename, doc_type="erro", source=source)
            doc.warnings.append(T(f"Could not read the PDF: {exc.__class__.__name__}",
                                  f"Não foi possível ler o PDF: {exc.__class__.__name__}"))
            return doc
        return self.extract_text(text, filename, source)

    # ── NF-first record building ─────────────────────────────────────────────
    @staticmethod
    def reconcile_by_value(docs: List[DocumentData], tolerance: float = 0.01):
        """Pair each invoice (NF) with the boleto of the same amount."""
        boletos = [d for d in docs if d.doc_type == "boleto"]
        nfs = [d for d in docs if d.doc_type in ("nota_fiscal", "combinado")]
        used = set()
        pairs = []
        for nf in nfs:
            match = None
            if nf.doc_type == "nota_fiscal":
                for i, b in enumerate(boletos):
                    if i not in used and abs(b.valor_num - nf.valor_num) <= tolerance:
                        match = b
                        used.add(i)
                        break
            pairs.append((nf, match))
        orphans = [b for i, b in enumerate(boletos) if i not in used]
        return pairs, orphans

    def build_records(self, docs: List[DocumentData]) -> Tuple[List[dict], List[DocumentData]]:
        pairs, orphans = self.reconcile_by_value(docs)
        records = []
        for nf, boleto in pairs:
            vencimento = nf.vencimento or (boleto.vencimento if boleto else "")
            warnings = list(nf.warnings)
            if not vencimento:
                warnings.append(T("No due date found (no matching boleto).",
                                  "Vencimento não encontrado (nenhum boleto com o mesmo valor)."))
            records.append({
                "fornecedor": nf.fornecedor,
                "vendor_key": nf.vendor_key,
                "unidade": nf.unidade,
                "cnpj": nf.cnpj,
                "numero": nf.numero,
                "emissao": nf.emissao,
                "vencimento": vencimento,
                "competencia": nf.competencia,
                "descricao": nf.descricao,
                "valor": nf.valor,
                "valor_num": nf.valor_num,
                "direct_to_fiscal": nf.direct_to_fiscal,
                "files": [nf.filename] + ([boleto.filename] if boleto else []),
                "source": nf.source,
                "warnings": warnings,
            })
        return records, orphans


# ── thread replies (Purchasing / Fiscal) ─────────────────────────────────────
PO_PATTERNS = [
    re.compile(r"(?:PEDIDO|PO|N[ºO]\s*PEDIDO)[^\d]*(\d+)", re.IGNORECASE),
    re.compile(r"(?:NF|Nota|N\.F\.?)\s*\d+\s+(\d{5,6})", re.IGNORECASE),
]
FISCAL_OK = re.compile(r"FISCAL\s*OK|PROCESSADO", re.IGNORECASE)


def parse_thread_reply(sender: str, body: str, purchasing: List[str], fiscal: List[str]) -> dict:
    """Decide what a reply in an invoice thread means.

    Same decision order as production: Purchasing replies carry a purchase
    order number; Fiscal replies say "FISCAL OK"; anything else from the
    supplier is a supplier reply (with or without a new attachment).
    """
    s = sender.lower()
    from_purchasing = any(p in s for p in purchasing)
    from_fiscal = any(f in s for f in fiscal)
    po = None
    for pat in PO_PATTERNS:
        m = pat.search(body)
        if m:
            po = m.group(1)
            break
    if po is None and from_purchasing:
        m = re.search(r"\b(\d{5,6})\b", body)
        po = m.group(1) if m else None
    if from_purchasing or (po and not from_fiscal):
        return {"kind": "purchasing", "po_number": po}
    if FISCAL_OK.search(body) or from_fiscal:
        return {"kind": "fiscal"}
    return {"kind": "supplier"}

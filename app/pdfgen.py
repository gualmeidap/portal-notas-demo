"""Tiny, dependency-free PDF writer.

The demo needs real PDF files (so the extraction pipeline reads actual PDF bytes
with pypdf, exactly like production does), but shipping binary fixtures in the
repo would make them opaque to review. Instead, every sample invoice is
described as plain text in `samples.py` and rendered here on demand.

Only what the demo needs is supported: one or more pages of left-aligned
Helvetica text, encoded as WinAnsi so Portuguese accents survive extraction.
"""
from __future__ import annotations

from typing import Iterable, List

PAGE_W, PAGE_H = 595, 842  # A4 in points
MARGIN_X, MARGIN_TOP = 50, 60
LINE_H = 15
LINES_PER_PAGE = (PAGE_H - 2 * MARGIN_TOP) // LINE_H


def _escape(line: str) -> bytes:
    raw = line.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _page_stream(lines: List[str]) -> bytes:
    out = [b"BT", b"/F1 10 Tf", f"{LINE_H} TL".encode(), f"{MARGIN_X} {PAGE_H - MARGIN_TOP} Td".encode()]
    for line in lines:
        size = 13 if line.isupper() and len(line) < 60 else 10
        out.append(f"/F1 {size} Tf".encode())
        out.append(b"(" + _escape(line) + b") Tj T*")
    out.append(b"ET")
    return b"\n".join(out)


def render_pdf(lines: Iterable[str]) -> bytes:
    """Render text lines into a valid PDF (multi-page when needed)."""
    lines = list(lines)
    pages = [lines[i:i + LINES_PER_PAGE] for i in range(0, len(lines), LINES_PER_PAGE)] or [[]]

    objects: List[bytes] = []
    # 1: catalog, 2: pages tree, 3: font; then (page, content) pairs
    kids = [4 + 2 * i for i in range(len(pages))]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(
        b"<< /Type /Pages /Kids [" + b" ".join(f"{k} 0 R".encode() for k in kids) + b"] /Count "
        + str(len(pages)).encode() + b" >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for i, page_lines in enumerate(pages):
        content_id = 5 + 2 * i
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        stream = _page_stream(page_lines)
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for num, body in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(buf)
    buf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        buf += f"{off:010d} 00000 n \n".encode()
    buf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(buf)

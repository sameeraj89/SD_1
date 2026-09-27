"""Phase 0 - Freeze. Fix the text, fingerprint it, record what was received.

I1 (input integrity): every file is SHA-256 hashed at freeze and the hash is
re-checked before every later phase; a mismatch aborts the run.
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass, field


class FreezeError(RuntimeError):
    pass


@dataclass
class FrozenDoc:
    index: int
    filename: str
    path: str
    sha256: str
    size: int
    media_type: str
    pages: int
    metadata: dict
    text_layer: bool            # False -> scanned; text comes from a transcription
    lines: list[dict] = field(default_factory=list)  # {"page": int, "line": int, "text": str}
    notes: list[str] = field(default_factory=list)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(ext, "application/octet-stream")


def _pdf_pages(path: str) -> tuple[list[str], dict]:
    from pypdf import PdfReader

    r = PdfReader(path)
    meta = {}
    if r.metadata:
        for k in ("/Author", "/Creator", "/Producer", "/CreationDate", "/ModDate", "/Title"):
            v = r.metadata.get(k)
            if v:
                meta[k.strip("/").lower()] = str(v)
    return [p.extract_text() or "" for p in r.pages], meta


def _docx_pages(path: str) -> tuple[list[str], dict]:
    try:
        import docx  # python-docx
    except ImportError as e:  # pragma: no cover
        raise FreezeError("python-docx is required to freeze .docx packs") from e
    d = docx.Document(path)
    cp = d.core_properties
    meta = {k: str(v) for k, v in {
        "author": cp.author, "created": cp.created, "modified": cp.modified, "title": cp.title,
    }.items() if v}
    return ["\n".join(p.text for p in d.paragraphs)], meta


def _to_lines(pages: list[str]) -> list[dict]:
    out = []
    for pno, text in enumerate(pages, 1):
        n = 0
        for raw in text.splitlines():
            if raw.strip():
                n += 1
                out.append({"page": pno, "line": n, "text": raw.rstrip()})
    return out


def freeze_file(index: int, path: str, transcriber=None) -> FrozenDoc:
    if not os.path.isfile(path):
        raise FreezeError(f"pack file not found: {path}")
    media = _media_type(path)
    meta: dict = {}
    if media == "application/pdf":
        pages, meta = _pdf_pages(path)
    elif media.endswith("wordprocessingml.document"):
        pages, meta = _docx_pages(path)
    elif media.startswith("text/"):
        with open(path, encoding="utf-8") as f:
            pages = f.read().split("\f")
    else:
        raise FreezeError(f"unsupported pack format: {path}")

    doc = FrozenDoc(
        index=index, filename=os.path.basename(path), path=os.path.abspath(path),
        sha256=sha256_file(path), size=os.path.getsize(path), media_type=media,
        pages=len(pages), metadata=meta, text_layer=True,
    )
    empty = [i + 1 for i, p in enumerate(pages) if len(p.strip()) < 20]
    if media == "application/pdf" and empty:
        # Scanned pages: read as rendered images, once, and freeze the transcription.
        if transcriber is None:
            raise FreezeError(
                f"{doc.filename}: pages {empty} have no text layer; a transcribing engine is required"
            )
        pages = transcriber(path, len(pages))
        doc.text_layer = False
        doc.notes.append(
            f"Pages {empty} carried no text layer; read as rendered images and the "
            "verbatim transcription frozen. Illegible or cropped values are marked [?]."
        )
    doc.lines = _to_lines(pages)
    if not doc.lines:
        raise FreezeError(f"{doc.filename}: no readable content")
    return doc


def verify(doc: FrozenDoc) -> None:
    """I1: abort on any mismatch between the file now and the file as frozen."""
    if not os.path.isfile(doc.path) or sha256_file(doc.path) != doc.sha256:
        raise FreezeError(f"input integrity violated: {doc.filename} changed after freeze")


# ------------------------------------------------------------ citations ---

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def render_for_reading(docs: list[FrozenDoc]) -> str:
    """The frozen text as every lens sees it: each line addressable by doc/page/line."""
    parts = []
    for d in docs:
        parts.append(f"=== DOCUMENT {d.index}: {d.filename} ({d.pages} pages) ===")
        for ln in d.lines:
            parts.append(f"[D{d.index} p{ln['page']} L{ln['line']}] {ln['text']}")
    return "\n".join(parts)


def locate(docs: list[FrozenDoc], quote: str) -> str | None:
    """Citation gate: return 'D1 p2 L14' if the quote exists in the frozen text.

    Matching tolerates whitespace, case, typographic quotes and line breaks
    (a quote may run across consecutive lines).
    """
    q = _norm(quote).strip("\"' .")
    if len(q) < 3:
        return None
    # Pass 1: a single line holds the quote.
    for d in docs:
        for ln in d.lines:
            if q in _norm(ln["text"]):
                return f"D{d.index} p{ln['page']} L{ln['line']}"
    # Pass 2: the quote runs across consecutive lines, starting on line i.
    for d in docs:
        normed = [_norm(ln["text"]) for ln in d.lines]
        for i in range(len(normed)):
            window = normed[i]
            for j in range(i + 1, min(i + 6, len(normed))):
                window = f"{window} {normed[j]}"
                if q in window:
                    ln = d.lines[i]
                    return f"D{d.index} p{ln['page']} L{ln['line']}"
    return None

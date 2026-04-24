# tools/pdf.py
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Iterable

from PyPDF2 import PdfReader, PdfWriter


# ─────────────────────────────────────────────────────────────
# Merge / validación
# ─────────────────────────────────────────────────────────────

def merge_pdfs(pdf_paths: Iterable[Path], output_path: Path) -> None:
    writer = PdfWriter()
    added_pages = False

    for path in pdf_paths:
        if not path.exists():
            raise FileNotFoundError(f"No existe el PDF: {path}")
        try:
            reader = PdfReader(str(path))
        except Exception as e:
            raise ValueError(f"PDF inválido o corrupto: {path}") from e

        for page in reader.pages:
            writer.add_page(page)
            added_pages = True

    if not added_pages:
        raise ValueError("No se agregaron páginas al PDF final.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        writer.write(f)


def get_pdf_page_count(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    try:
        return len(PdfReader(str(path)).pages)
    except Exception as e:
        raise ValueError(f"No se pudo leer el PDF: {path}") from e


def is_valid_pdf(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        PdfReader(str(path))
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# Extracción de texto
# ─────────────────────────────────────────────────────────────

def _get_pages_text(path: Path) -> list[str]:
    """
    Extrae el texto de cada página.
    Intenta PyMuPDF (mejor calidad) → pypdf → PyPDF2.
    """
    abs_path = str(path.resolve())

    try:
        import fitz  # type: ignore  (PyMuPDF)
        doc = fitz.open(abs_path)
        pages = []
        for i in range(len(doc)):
            try:
                pages.append(doc.load_page(i).get_text("text") or "")
            except Exception:
                pages.append("")
        doc.close()
        return pages
    except Exception:
        pass

    try:
        from pypdf import PdfReader as _Reader  # type: ignore
        return [p.extract_text() or "" for p in _Reader(abs_path).pages]
    except Exception:
        pass

    try:
        return [p.extract_text() or "" for p in PdfReader(abs_path).pages]
    except Exception as e:
        raise RuntimeError(
            f"No se pudo extraer texto del PDF (fitz/pypdf/PyPDF2 fallaron): {e}"
        )


# ─────────────────────────────────────────────────────────────
# Búsqueda de mensaje por nombre de cliente
# ─────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()


def find_message_for_client(path: Path, client_name: str) -> dict:
    """
    Busca en el PDF la página que contiene el mensaje del cliente.

    Estrategia (en orden):
      1. Coincidencia exacta del nombre normalizado.
      2. Coincidencia por apellido(s) (últimas dos palabras).
      3. Coincidencia difusa con difflib.

    Devuelve:
      { "found": bool, "page_idx": int|None,
        "text": str, "snippet": str, "errors": list[str] }
    """
    result: dict = {
        "found": False, "page_idx": None,
        "text": "", "snippet": "", "errors": [],
    }

    if not client_name or not client_name.strip():
        return result

    if not path.exists():
        result["errors"].append(f"PDF no existe: {path}")
        return result

    try:
        pages = _get_pages_text(path)
    except Exception as e:
        result["errors"].append(str(e))
        return result

    client_norm = _normalize(client_name)

    def _set_found(i: int) -> dict:
        txt = pages[i].strip()
        result.update({
            "found": True,
            "page_idx": i,
            "text": txt,
            "snippet": (txt[:160] + "...") if len(txt) > 160 else txt,
        })
        return result

    # 1. Exacta
    for i, pg in enumerate(pages):
        if client_norm in _normalize(pg):
            return _set_found(i)

    # 2. Por apellido(s)
    parts = [p for p in client_name.split() if p.strip()]
    tokens: list[str] = []
    if len(parts) >= 2:
        tokens = [_normalize(parts[-1]), _normalize(parts[-2])]
    elif parts:
        tokens = [_normalize(parts[0])]

    for token in tokens:
        for i, pg in enumerate(pages):
            if token in _normalize(pg):
                return _set_found(i)

    # 3. Difusa
    try:
        import difflib
        snippets_norm = [_normalize(pg[:300]) for pg in pages]
        candidates = [client_norm] + [_normalize(p) for p in parts if len(p) >= 3]
        for cand in candidates:
            matches = difflib.get_close_matches(cand, snippets_norm, n=1, cutoff=0.6)
            if matches:
                return _set_found(snippets_norm.index(matches[0]))
    except Exception:
        pass

    return result
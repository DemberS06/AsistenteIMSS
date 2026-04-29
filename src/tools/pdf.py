# tools/pdf.py
from __future__ import annotations

import re
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
# Normalización de texto
# ─────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    """Normaliza texto: sin acentos, minúsculas"""
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()

def normalize_paragraph_breaks(text: str) -> str:
    """
    Normaliza los saltos de línea en el texto extraído de PDF:
    
    - Une líneas que son parte del mismo párrafo (saltos shift+enter)
    - Mantiene separación entre párrafos verdaderos (líneas vacías)
    - Preserva listas y formato estructurado (BANCO:, NÚMERO:, etc.)
    """
    if not text or not text.strip():
        return ""
    
    lines = text.split('\n')
    
    # Patrones que indican que una línea debe estar SOLA (no unir con anterior/siguiente)
    standalone_patterns = [
        r'^(BANCO|NÚMERO|CUENTA|NOMBRE|TARJETA|CLABE):',  # Campos estructurados
        r'^\d+\.$',  # Números con punto al final (ej: "65509866769.")
    ]
    
    # Patrones que terminan un párrafo definitivamente
    hard_end_patterns = [
        r'[.!?]$',  # Puntuación fuerte
    ]
    
    # Patrones que inician un nuevo párrafo
    new_paragraph_patterns = [
        r'^[¡¿⚠]',  # Signos especiales de inicio
    ]
    
    def is_standalone_line(line: str) -> bool:
        """Línea que debe estar sola (datos bancarios, etc.)"""
        for pattern in standalone_patterns:
            if re.match(pattern, line):
                return True
        return False
    
    def ends_paragraph(line: str) -> bool:
        """Línea que termina un párrafo"""
        for pattern in hard_end_patterns:
            if re.search(pattern, line):
                return True
        return False
    
    def starts_new_paragraph(line: str) -> bool:
        """Línea que inicia un nuevo párrafo"""
        for pattern in new_paragraph_patterns:
            if re.match(pattern, line):
                return True
        return False
    
    # Procesar líneas
    result_lines = []
    current_paragraph = []
    
    for line in lines:
        stripped = line.strip()
        
        # Línea vacía -> cerrar párrafo actual y agregar separación
        if not stripped:
            if current_paragraph:
                result_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            # Agregar línea vacía solo si no es la primera o si ya hay contenido
            if result_lines:
                result_lines.append('')
            continue
        
        # Línea standalone (BANCO:, NÚMERO:, etc.) -> cerrar párrafo y agregar sola
        if is_standalone_line(stripped):
            if current_paragraph:
                result_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            result_lines.append(stripped)
            continue
        
        # Línea que inicia nuevo párrafo (¡, ⚠, etc.) -> cerrar anterior
        if starts_new_paragraph(stripped):
            if current_paragraph:
                result_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            current_paragraph.append(stripped)
            continue
        
        # Agregar al párrafo actual
        current_paragraph.append(stripped)
        
        # Si termina con puntuación fuerte -> cerrar párrafo
        if ends_paragraph(stripped):
            result_lines.append(' '.join(current_paragraph))
            current_paragraph = []
    
    # Agregar último párrafo si quedó algo
    if current_paragraph:
        result_lines.append(' '.join(current_paragraph))
    
    # Unir y limpiar líneas vacías múltiples
    result = '\n'.join(result_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)  # Max 2 saltos consecutivos
    
    return result.strip()

def remove_first_line(text: str) -> str:
    """
    Elimina la primera línea del texto.
    Útil para quitar el ID o saludo personalizado del mensaje.
    """
    if not text or not text.strip():
        return ""
    
    lines = text.split('\n', 1)
    if len(lines) <= 1:
        return ""
    
    return lines[1].strip()

# ─────────────────────────────────────────────────────────────
# Búsqueda de mensaje por nombre de cliente
# ─────────────────────────────────────────────────────────────

def find_message_for_client(path: Path, client_name: str) -> dict:
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


# ─────────────────────────────────────────────────────────────
# Búsqueda de mensaje por ID de cliente
# ─────────────────────────────────────────────────────────────

def find_message_by_id(path: Path, client_id: str) -> dict:
    result: dict = {
        "found": False,
        "page_idx": None,
        "text": "",
        "snippet": "",
        "errors": [],
    }

    print("id: "+client_id)

    if not client_id or not str(client_id).strip():
        result["errors"].append("ID de cliente vacío")
        return result

    if not path.exists():
        result["errors"].append(f"PDF no existe: {path}")
        return result

    try:
        pages = _get_pages_text(path)
    except Exception as e:
        result["errors"].append(str(e))
        return result

    # Normalizar el ID para comparación
    id_search = str(client_id).strip().lower()

    # Buscar en cada página
    for i, page_text in enumerate(pages):
        if not page_text.strip():
            continue
        
        # Obtener la primera línea
        first_line = page_text.split('\n', 1)[0].strip().lower()
        
        # Verificar si el ID está en la primera línea
        if id_search in first_line:
            print("data: "+id_search+"<->"+first_line)
            result.update({
                "found": True,
                "page_idx": i,
                "text": page_text.strip(),
                "snippet": (page_text[:160] + "...") if len(page_text) > 160 else page_text.strip(),
            })
            return result

    result["errors"].append(f"No se encontró mensaje con ID: {client_id}")
    return result


# ─────────────────────────────────────────────────────────────
# Función principal de extracción
# ─────────────────────────────────────────────────────────────

def extract_message(
    pdf_path: Path,
    identifier: str,
    search_by: str = "name",
    remove_first_line_flag: bool = False,
    normalize_breaks: bool = True
) -> dict:
    result = {
        "success": False,
        "message": "",
        "raw_message": "",
        "page_idx": None,
        "errors": []
    }
    
    # Buscar mensaje según el método
    if search_by == "id":
        search_result = find_message_by_id(pdf_path, identifier)
    else:  # "name"
        search_result = find_message_for_client(pdf_path, identifier)
    
    if not search_result["found"]:
        result["errors"] = search_result["errors"]
        return result
    
    # Mensaje encontrado
    raw_message = search_result["text"]
    result["raw_message"] = raw_message
    result["page_idx"] = search_result["page_idx"]
    
    # Procesar mensaje
    processed = raw_message
    
    # 1. Eliminar primera línea si se solicita
    if remove_first_line_flag:
        processed = remove_first_line(processed)
    
    # 2. Normalizar párrafos
    if normalize_breaks:
        processed = normalize_paragraph_breaks(processed)
    
    result["message"] = processed
    result["success"] = True
    
    return result
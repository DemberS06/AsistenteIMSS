# tools/pdf.py
from pathlib import Path
from typing import Iterable
from PyPDF2 import PdfReader, PdfWriter


def merge_pdfs(pdf_paths: Iterable[Path], output_path: Path) -> None:
    writer = PdfWriter()
    added_pages = False

    for path in pdf_paths:
        if not path.exists():
            raise FileNotFoundError(f"No existe el PDF: {path}")

        try:
            reader = PdfReader(path)
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
        reader = PdfReader(path)
        return len(reader.pages)
    except Exception as e:
        raise ValueError(f"No se pudo leer el PDF: {path}") from e


def is_valid_pdf(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        PdfReader(path)
        return True
    except Exception:
        return False
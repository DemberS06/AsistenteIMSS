from pathlib import Path
from typing import Iterable
from PyPDF2 import PdfReader, PdfWriter


def merge_pdfs(pdf_paths: Iterable[Path], output_path: Path) -> bool:
    try:
        writer = PdfWriter()

        for path in pdf_paths:
            if not path.exists():
                continue

            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)

        if not writer.pages:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("wb") as f:
            writer.write(f)

        return True

    except Exception:
        return False


def get_pdf_page_count(path: Path) -> int:
    try:
        if not path.exists():
            return 0

        reader = PdfReader(path)
        return len(reader.pages)

    except Exception:
        return 0


def is_valid_pdf(path: Path) -> bool:
    try:
        if not path.exists():
            return False

        PdfReader(path)
        return True

    except Exception:
        return False
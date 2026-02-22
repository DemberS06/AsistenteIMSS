from pathlib import Path
import shutil
from typing import Optional


def ensure_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def file_exists(path: Path) -> bool:
    return path.exists()


def delete_file(path: Path) -> bool:
    try:
        if path.exists():
            path.unlink()
        return True
    except Exception:
        return False


def move_file(source: Path, destination: Path) -> bool:
    try:
        if not source.exists():
            return False

        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            destination.unlink()

        shutil.move(str(source), str(destination))
        return True
    except Exception:
        return False


def copy_file(source: Path, destination: Path) -> bool:
    try:
        if not source.exists():
            return False

        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            destination.unlink()

        shutil.copy2(source, destination)
        return True
    except Exception:
        return False


def list_files(directory: Path, extension: Optional[str] = None) -> list[Path]:
    try:
        if not directory.exists():
            return []

        if extension:
            extension = extension.lstrip(".")
            return list(directory.glob(f"*.{extension}"))

        return [p for p in directory.iterdir() if p.is_file()]
    except Exception:
        return []
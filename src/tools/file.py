# tools/file.py
from pathlib import Path
import shutil
from typing import Optional


def ensure_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise OSError(f"No se pudo crear el directorio: {path}") from e


def file_exists(path: Path) -> bool:
    return path.exists()


def delete_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    
    try:
        path.unlink()
    except Exception as e:
        raise OSError(f"No se pudo eliminar el archivo: {path}") from e


def move_file(source: Path, destination: Path):
    if not source.exists():
        raise FileNotFoundError(f"No existe el archivo origen: {source}")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            destination.unlink()

        shutil.move(str(source), str(destination))
    except Exception as e:
        raise OSError(f"No se pudo mover el archivo de {source} a {destination}") from e


def copy_file(source: Path, destination: Path):
    if not source.exists():
        raise FileNotFoundError(f"No existe el archivo origen: {source}")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            destination.unlink()

        shutil.copy2(source, destination)
    except Exception as e:
        raise OSError(f"No se pudo copiar el archivo de {source} a {destination}") from e


def list_files(directory: Path, extension: Optional[str] = None) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"No existe el directorio: {directory}")
    try:
        if extension:
            extension = extension.lstrip(".")
            return list(directory.glob(f"*.{extension}"))

        return [p for p in directory.iterdir() if p.is_file()]
    except Exception as e:
        raise OSError(f"No se pudo listar archivos en: {directory}") from e
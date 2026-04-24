# tools/excel.py
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import tempfile
import shutil
import time


class ExcelTools:
    def __init__(self, path: str, has_header: bool = True, save_timeout: float = 10.0):
        self.path = Path(path).resolve()
        self.has_header = has_header
        self.save_timeout = float(save_timeout)
        self.df: pd.DataFrame | None = None
        self.current_index: int = 0

    # =========================
    # I/O
    # =========================

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"No existe el archivo Excel: {self.path}")

        try:
            if self.has_header:
                self.df = pd.read_excel(self.path, engine="openpyxl")
            else:
                self.df = pd.read_excel(self.path, header=None, engine="openpyxl")
        except Exception as e:
            raise RuntimeError(f"Error leyendo Excel: {self.path}") from e

        self.df = self.df.fillna("")
        self.df = self.df.reset_index(drop=True)
        self.current_index = 0
        return self.df

    def save(self) -> Path:
        if self.df is None:
            raise ValueError("No hay DataFrame cargado para guardar.")

        folder = self.path.parent
        end_time = time.time() + self.save_timeout

        while True:
            fd, tmp_path = tempfile.mkstemp(suffix=".xlsx", dir=folder)
            os.close(fd)                          # cerrar fd antes de tocar el archivo
            Path(tmp_path).unlink(missing_ok=True)

            try:
                self.df.to_excel(tmp_path, index=False, engine="openpyxl")
                shutil.move(tmp_path, self.path)
                return self.path

            except PermissionError as e:
                if time.time() > end_time:
                    raise PermissionError(
                        f"No se pudo guardar el Excel por bloqueo: {self.path}"
                    ) from e
                time.sleep(0.5)

            except Exception as e:
                raise RuntimeError("Error inesperado guardando Excel.") from e

    def reload(self) -> None:
        self.load()

    # =========================
    # Columnas
    # =========================

    def ensure_columns(self, names: list[str]) -> None:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        for name in names:
            if name not in self.df.columns:
                self.df[name] = ""

    # =========================
    # Filas / CRUD
    # =========================

    def row_count(self) -> int:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")
        return len(self.df)

    def get_row(self, index: int) -> dict:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        if not 0 <= index < len(self.df):
            raise IndexError("Índice fuera de rango.")

        self.current_index = index
        row = self.df.iloc[index].to_dict()

        return {k: self._to_string(v) for k, v in row.items()}  

    def next_row(self) -> dict | None:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        if self.current_index + 1 >= len(self.df):
            return None

        return self.get_row(self.current_index + 1)

    def prev_row(self) -> dict | None:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        if self.current_index - 1 < 0:
            return None

        return self.get_row(self.current_index - 1)

    def add_row(self, data: dict | None = None) -> int:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        if data is None:
            data = {}

        self.ensure_columns(list(data.keys()))

        row = {c: "" for c in self.df.columns}
        for k, v in data.items():
            row[k] = "" if pd.isna(v) else v

        self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
        self.current_index = len(self.df) - 1
        return self.current_index

    def insert_row(self, index: int, data: dict | None = None) -> int:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        if not 0 <= index <= len(self.df):
            raise IndexError("Índice fuera de rango.")

        if data is None:
            data = {}

        self.ensure_columns(list(data.keys()))

        row = {c: "" for c in self.df.columns}
        for k, v in data.items():
            row[k] = "" if pd.isna(v) else v

        top = self.df.iloc[:index]
        bottom = self.df.iloc[index:]
        self.df = pd.concat([top, pd.DataFrame([row]), bottom], ignore_index=True)

        self.current_index = index
        return index

    def update_row(self, index: int, data: dict) -> None:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        if not 0 <= index < len(self.df):
            raise IndexError("Índice fuera de rango.")

        self.ensure_columns(list(data.keys()))

        for col, val in data.items():
            self.df.at[index, col] = "" if pd.isna(val) else val

        if "UltimaActualizacion" in self.df.columns:
            self.df.at[index, "UltimaActualizacion"] = datetime.now().isoformat(
                sep=" ", timespec="seconds"
            )

    def delete_row(self, index: int) -> None:
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        if not 0 <= index < len(self.df):
            raise IndexError("Índice fuera de rango.")

        self.df = self.df.drop(index).reset_index(drop=True)

        if self.current_index >= len(self.df):
            self.current_index = len(self.df) - 1 if len(self.df) > 0 else 0

    # =========================
    # Búsqueda
    # =========================

    def find_by(self, column: str, value, first_only: bool = True):
        if self.df is None:
            raise ValueError("DataFrame no cargado.")

        if column not in self.df.columns:
            raise ValueError(f"La columna '{column}' no existe.")

        mask = self.df[column] == value
        indices = list(self.df.index[mask])

        if first_only:
            return indices[0] if indices else None

        return indices

    # =========================
    # Representación
    # =========================

    def __repr__(self):
        rows = 0 if self.df is None else len(self.df)
        return f"<ExcelTools path={self.path} rows={rows} idx={self.current_index}>"
    
    def _to_string(self, value) -> str:
        if value is None:
            return ""

        # pandas NaN
        try:
            import pandas as pd
            if pd.isna(value):
                return ""
        except Exception:
            pass

        # float tipo 123.0 -> "123"
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value)

        # int
        if isinstance(value, int):
            return str(value)

        # bool
        if isinstance(value, bool):
            return "1" if value else "0"

        # fallback
        return str(value).strip()
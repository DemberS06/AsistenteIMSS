# modules/excel_tools.py
import os
import tempfile
import shutil
import time
import traceback
from datetime import datetime
import pandas as pd

_error_log_path = os.path.abspath("error.log")


def _log_error(text: str):
    try:
        with open(_error_log_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(sep=' ', timespec='seconds')} - {text}\n")
    except Exception:
        pass


class ExcelTools:
    def __init__(self, path=None, has_header=True, save_timeout: float = 10.0):
        self.path = os.path.abspath(path) if path else None
        self.has_header = bool(has_header)
        self.save_timeout = float(save_timeout)
        self.df = None
        self.current_index = 0

        if self.path:
            try:
                self.load_excel()
            except Exception as e:
                _log_error(f"__init__ load_excel error: {e}\n{traceback.format_exc()}")

    # ---------------- I/O ----------------
    def load_excel(self):
        if not self.path:
            raise ValueError("No se indicó ruta de Excel para cargar.")

        try:
            if self.has_header:
                self.df = pd.read_excel(self.path, engine="openpyxl")
            else:
                self.df = pd.read_excel(self.path, header=None, engine="openpyxl")
        except FileNotFoundError:
            self.df = pd.DataFrame()
        except Exception as e:
            _log_error(f"load_excel read error: {e}\n{traceback.format_exc()}")
            self.df = pd.DataFrame()

        try:
            self.df = self.df.fillna("")
        except Exception:
            pass

        self._normalize_column_names()
        self._ensure_cache_columns()
        self.df = self.df.reset_index(drop=True)
        self.current_index = 0
        return self.df

    def save_excel_atomic(self):
        if self.df is None:
            return
        if not self.path:
            raise ValueError("No se indicó ruta de Excel para guardar.")
        folder = os.path.dirname(self.path) or "."
        basename = os.path.basename(self.path)
        end_time = time.time() + self.save_timeout

        try:
            if os.path.exists(self.path):
                bak_path = f"{self.path}.bak"
                shutil.copy2(self.path, bak_path)
        except Exception as e:
            _log_error(f"save backup warning: {e}\n{traceback.format_exc()}")

        while True:
            fd, tmp_path = tempfile.mkstemp(suffix=".xlsx", dir=folder)
            os.close(fd)
            try:
                self.df.to_excel(tmp_path, index=False, engine="openpyxl")
                shutil.move(tmp_path, self.path)
                return self.path
            except PermissionError as pe:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                if time.time() > end_time:
                    msg = f"PermissionError guardando Excel '{basename}': {pe}"
                    _log_error(msg + "\n" + traceback.format_exc())
                    raise PermissionError(msg)
                time.sleep(0.5)
                continue
            except Exception as e:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                _log_error(f"save_excel_atomic error: {e}\n{traceback.format_exc()}")
                raise

    def save(self):
        return self.save_excel_atomic()

    def reload_from_disk(self):
        if not self.path or not os.path.exists(self.path):
            raise FileNotFoundError(f"Archivo Excel no existe: {self.path}")
        old_index = self.current_index
        self.load_excel()
        if self.df is not None and 0 <= old_index < len(self.df):
            self.current_index = old_index
        else:
            self.current_index = 0

    # ---------------- columnas ----------------
    def _normalize_column_names(self):
        if self.df is None or self.df.empty:
            return
        cols = list(self.df.columns)
        lower_map = {str(c).lower(): c for c in cols}

    def _ensure_cache_columns(self):
        if self.df is None:
            return
        for c in ("Estado", "IntentosCaptcha", "Archivo", "CarpetaPDF", "UltimaActualizacion"):
            if c not in self.df.columns:
                self.df[c] = ""

    def ensure_columns(self, names):
        if self.df is None:
            self.df = pd.DataFrame()
        for n in names:
            if n not in self.df.columns:
                self.df[n] = ""
        return list(self.df.columns)

    # ---------------- filas / CRUD ----------------
    def row_count(self):
        return 0 if self.df is None else len(self.df)

    def get_row(self, index):
        if self.df is None:
            return None
        if index < 0 or index >= len(self.df):
            return None
        self.current_index = index
        return self.df.iloc[index].to_dict()

    def next_row(self):
        if self.df is None:
            return None
        if self.current_index + 1 >= len(self.df):
            return None
        return self.get_row(self.current_index + 1)

    def prev_row(self):
        if self.df is None:
            return None
        if self.current_index - 1 < 0:
            return None
        return self.get_row(self.current_index - 1)

    def add_row(self, data=None):
        if self.df is None:
            self.df = pd.DataFrame()
        if data is None:
            data = {}
        for k in list(data.keys()):
            if k not in self.df.columns:
                self.df[k] = ""
        row = {c: "" for c in list(self.df.columns)}
        for k, v in data.items():
            row[k] = "" if pd.isna(v) else v
        self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
        self.current_index = len(self.df) - 1
        return self.current_index

    def update_row(self, index, data: dict):
        if self.df is None:
            return False
        if not isinstance(index, int) or index < 0 or index >= len(self.df):
            return False
        for col in data.keys():
            if col not in self.df.columns:
                self.df[col] = ""
        row_label = self.df.index[index]
        for col, val in data.items():
            try:
                if pd.isna(val):
                    write_val = ""
                else:
                    write_val = val
            except Exception:
                write_val = val if val is not None else ""
            self.df.at[row_label, col] = write_val
        if "UltimaActualizacion" in self.df.columns:
            self.df.at[row_label, "UltimaActualizacion"] = datetime.now().isoformat(sep=" ", timespec="seconds")
        return True

    def insert_row(self, idx, data=None):
        if data is None:
            data = {}
        if self.df is None:
            return self.add_row(data)
        for k in data.keys():
            if k not in self.df.columns:
                self.df[k] = ""
        row = {c: "" for c in self.df.columns}
        for k, v in data.items():
            row[k] = "" if pd.isna(v) else v
        top = self.df.iloc[:idx]
        bottom = self.df.iloc[idx:]
        self.df = pd.concat([top, pd.DataFrame([row]), bottom], ignore_index=True)
        self.current_index = idx
        return idx

    def update_pdf_entry(self, index=None, dest_folder: str = None, pdf_to_save: str = None):
        try:
            if self.df is None:
                self.df = pd.DataFrame()

            if dest_folder:
                try:
                    dest_folder = os.path.abspath(dest_folder)
                except Exception:
                    dest_folder = str(dest_folder)

            if pdf_to_save:
                try:
                    pdf_to_save = os.path.abspath(pdf_to_save)
                except Exception:
                    pdf_to_save = str(pdf_to_save)

            self.ensure_columns(["CarpetaPDF", "PDF", "UltimaActualizacion"])

            valid_index = None
            try:
                if index is not None:
                    idx_int = int(index)
                    if 0 <= idx_int < self.row_count():
                        valid_index = idx_int
            except Exception:
                valid_index = None

            if valid_index is None:
                valid_index = self.add_row({})

            row_label = self.df.index[valid_index]
            if dest_folder:
                self.df.at[row_label, "CarpetaPDF"] = dest_folder
            if pdf_to_save:
                self.df.at[row_label, "PDF"] = pdf_to_save

            try:
                self.df.at[row_label, "UltimaActualizacion"] = datetime.now().isoformat(sep=" ", timespec="seconds")
            except Exception:
                pass

            try:
                if hasattr(self, "save"):
                    self.save()
                else:
                    # fallback
                    self.save_excel_atomic()
            except Exception as e:
                _log_error(f"update_pdf_entry: error guardando Excel: {e}\n{traceback.format_exc()}")
                return None

            try:
                self.current_index = int(valid_index)
            except Exception:
                try:
                    self.current_index = valid_index
                except Exception:
                    pass

            return int(valid_index)
        except Exception as e:
            _log_error(f"update_pdf_entry: excepcion: {e}\n{traceback.format_exc()}")
            return None

    # ---------------- util ----------------
    def find_by(self, column, value, first_only=True):
        if self.df is None or column not in self.df.columns:
            return None if first_only else []
        mask = self.df[column] == value
        idxs = list(self.df.index[mask])
        if first_only:
            return idxs[0] if idxs else None
        return idxs

    def __repr__(self):
        rows = 0 if self.df is None else len(self.df)
        return f"<ExcelTools path={self.path} rows={rows} idx={self.current_index}>"

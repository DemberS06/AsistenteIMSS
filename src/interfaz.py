# interfaz.py
import sys
import traceback
import time
import os
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QInputDialog,
    QTextEdit, QGroupBox, QListWidget
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

from modules.excel_tools import ExcelTools
from modules.web_management import WebManager
from modules.pdf_tools import PDFTools
from selenium.webdriver.common.by import By
from modules.whatsapp_manager import WhatsAppManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

def _user_data_dir():
    base = os.getenv("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    appdir = os.path.join(base, "AsistenteIMSS")
    try:
        os.makedirs(appdir, exist_ok=True)
    except Exception:
        pass
    return appdir

DATA_DIR = _user_data_dir()


def excepcion_no_manejada(exc_type, exc_value, exc_tb):
    texto = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        log_path = os.path.join(DATA_DIR, "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write(texto)
            f.write("\n")
    except Exception:
        pass
    try:
        QMessageBox.critical(None, "Error no manejado",f"Ocurrió un error:\n{exc_value}\n\nRevisa el log en:\n{os.path.join(DATA_DIR, 'error.log')}")
    except Exception:
        print("Error crítico y no se pudo mostrar diálogo Qt:\n", texto)
    sys.exit(1)

sys.excepthook = excepcion_no_manejada

class ExcelInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente IMSS")
        self.setGeometry(150, 80, 1200, 720)

        # módulos
        self.excel = None
        
        self.web = WebManager(headless=False, temp_download_dir=os.path.join(DATA_DIR, "_tmp_downloads"))
        self.pdf_tools = PDFTools()
        self.download_folder = None

        self.whatsapp = WhatsAppManager(
            webmanager=self.web,
            profile_dir=os.path.join(DATA_DIR, "whatsapp_profile"),
            headless=False
        )

        main_layout = QHBoxLayout()

        # ----------------- Panel 1: Manejo Excel / edición fila -----------------
        self.panel1 = QGroupBox("Cliente")
        p1_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        self.btn_open_excel = QPushButton("Abrir Excel")
        self.btn_open_excel.clicked.connect(self.load_excel)
        btn_layout.addWidget(self.btn_open_excel)

        self.btn_open_pdf_dir = QPushButton("Abrir PDF")
        self.btn_open_pdf_dir.clicked.connect(self.open_pdf_dir)
        btn_layout.addWidget(self.btn_open_pdf_dir)

        p1_layout.addLayout(btn_layout)

        self.name_line = QLineEdit(); self.name_line.setPlaceholderText("Nombre del cliente")
        self.number_line = QLineEdit(); self.number_line.setPlaceholderText("Numero de teléfono")
        self.curp_line = QLineEdit(); self.curp_line.setPlaceholderText("CURP")
        self.rfc_line = QLineEdit(); self.rfc_line.setPlaceholderText("RFC")
        self.nss_line = QLineEdit(); self.nss_line.setPlaceholderText("NSS")
        self.email_line = QLineEdit(); self.email_line.setPlaceholderText("Email")
        for w in [self.name_line, self.number_line, self.curp_line, self.rfc_line, self.nss_line, self.email_line]:
            p1_layout.addWidget(w)

        self.pdf_dir_label = QLabel("Dirección de PDF: (ninguna)")
        self.word_path_label = QLabel("Dirección de Word: (ninguna)")
        self.pdf_dir_label.setWordWrap(True)
        p1_layout.addWidget(self.pdf_dir_label)

        save_new_layout = QHBoxLayout()
        self.btn_save_changes = QPushButton("Guardar cambios")
        self.btn_save_changes.clicked.connect(self.save_changes)
        save_new_layout.addWidget(self.btn_save_changes)

        self.btn_new_client = QPushButton("Nuevo cliente")
        self.btn_new_client.clicked.connect(self.new_client)
        save_new_layout.addWidget(self.btn_new_client)
        p1_layout.addLayout(save_new_layout)

        nav_layout = QHBoxLayout()
        self.btn_prev_client = QPushButton("Cliente anterior")
        self.btn_prev_client.clicked.connect(self.prev_row)
        nav_layout.addWidget(self.btn_prev_client)

        self.btn_next_client = QPushButton("Siguiente Cliente")
        self.btn_next_client.clicked.connect(self.next_row)
        nav_layout.addWidget(self.btn_next_client)

        self.btn_goto_client = QPushButton("Ir al Cliente X")
        self.btn_goto_client.clicked.connect(self.goto_row)
        nav_layout.addWidget(self.btn_goto_client)

        p1_layout.addLayout(nav_layout)

        self.panel1.setLayout(p1_layout)
        main_layout.addWidget(self.panel1, 3)

        # ----------------- Panel 2: Descargas / Captcha / Acciones web -----------------
        self.panel2 = QGroupBox("Registro")
        p2_layout = QVBoxLayout()

        df_layout = QHBoxLayout()
        self.btn_select_download_folder = QPushButton("Seleccionar carpeta de descargas final")
        self.btn_select_download_folder.clicked.connect(self.select_download_folder)
        df_layout.addWidget(self.btn_select_download_folder)
        p2_layout.addLayout(df_layout)

        self.selected_download_label = QLabel("Carpeta final: (ninguna)")
        self.selected_download_label.setWordWrap(True)
        p2_layout.addWidget(self.selected_download_label)

        self.captcha_label = QLabel("Captcha aquí")
        self.captcha_label.setAlignment(Qt.AlignCenter)
        self.captcha_label.setFixedSize(440, 80)
        self.captcha_label.setStyleSheet("border: 1px solid black;")
        p2_layout.addWidget(self.captcha_label)

        self.captcha_input = QLineEdit(); self.captcha_input.setPlaceholderText("Escribe el captcha")
        p2_layout.addWidget(self.captcha_input)

        buttons2_layout = QHBoxLayout()
        self.btn_register_client = QPushButton("Registrar Cliente")
        self.btn_register_client.clicked.connect(self.registration)
        buttons2_layout.addWidget(self.btn_register_client)

        self.btn_download_pdf = QPushButton("Descargar PDF")
        self.btn_download_pdf.clicked.connect(self.get_pdf)
        buttons2_layout.addWidget(self.btn_download_pdf)

        p2_layout.addLayout(buttons2_layout)

        more_layout = QHBoxLayout()
        self.btn_open_page = QPushButton("Abrir Pagina")
        self.btn_open_page.clicked.connect(self.open_web_page)
        more_layout.addWidget(self.btn_open_page)

        self.btn_show_captcha = QPushButton("Mostrar Captcha")
        self.btn_show_captcha.clicked.connect(self.show_captcha)
        more_layout.addWidget(self.btn_show_captcha)

        p2_layout.addLayout(more_layout)

        self.panel2.setLayout(p2_layout)
        main_layout.addWidget(self.panel2, 2)

        # ----------------- Panel 3: Previsualización Word + Enviar -----------------
        self.panel3 = QGroupBox("Mensaje")
        p3_layout = QVBoxLayout()
        
        self.btn_select_global_pdf = QPushButton("Seleccionar PDF de mensajes")
        self.btn_select_global_pdf.clicked.connect(self.select_global_pdf_file)
        p3_layout.addWidget(self.btn_select_global_pdf)

        self.global_pdf_label = QLabel("PDF global: (ninguno)")
        self.global_pdf_label.setWordWrap(True)
        p3_layout.addWidget(self.global_pdf_label)
       
        self.word_preview = QTextEdit()
        self.word_preview.setReadOnly(True)
        self.word_preview.setPlaceholderText("Aquí se mostrará el texto del mensaje.")
        p3_layout.addWidget(self.word_preview)

        self.btn_send_message = QPushButton("Enviar mensaje")
        self.btn_send_message.clicked.connect(self.send_message)
        p3_layout.addWidget(self.btn_send_message)

        self.btn_open_whatsapp = QPushButton("Abrir WhatsApp Web")
        self.btn_open_whatsapp.clicked.connect(lambda: self._ui_open_whatsapp())
        p3_layout.addWidget(self.btn_open_whatsapp)

        range_row = QHBoxLayout()
        self.range_from = QLineEdit(); self.range_from.setPlaceholderText("Desde")
        self.range_to   = QLineEdit(); self.range_to.setPlaceholderText("Hasta")
        range_row.addWidget(self.range_from)
        range_row.addWidget(self.range_to)
        p3_layout.addLayout(range_row)

        self.btn_send_range = QPushButton("Enviar mensajes en el rango")
        self.btn_send_range.clicked.connect(self.send_range)
        p3_layout.addWidget(self.btn_send_range)

        self.panel3.setLayout(p3_layout)
        main_layout.addWidget(self.panel3, 3)

        # Estado inferior
        outer_layout = QVBoxLayout()
        outer_layout.addLayout(main_layout)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: green;")
        outer_layout.addWidget(self.status_label)

        self.setLayout(outer_layout)

        # inicializaciones internas
        self._refresh_client_list()

    # ------------------- Excel -------------------
    def load_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona archivo Excel", "", "Archivos Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            self.excel = ExcelTools(path, has_header=True)
            if self.excel.df is not None:
                if "WORD" not in list(self.excel.df.columns):
                    self.excel.df["WORD"] = ""
                if "PDF" not in list(self.excel.df.columns):
                    self.excel.df["PDF"] = ""
                try:
                    if hasattr(self.excel, "save"):
                        self.excel.save()
                    else:
                        self.excel.save_excel_atomic()
                except Exception:
                    pass

            self._refresh_client_list()
            self.status_label.setText(f"Excel cargado: {os.path.basename(path)}")
            self.show_row_index(0)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo cargar el Excel:\n{e}")

    def show_row_index(self, index):
        if self.excel is None or self.excel.df is None:
            return
        if not isinstance(index, int):
            try:
                index = int(index)
            except Exception:
                return

        row = self.excel.get_row(index)
        if row is None:
            QMessageBox.information(self, "Info", "Fila inválida.")
            return

        def clean_val(v):
            try:
                import unicodedata, numbers
                try:
                    import pandas as _pd
                    if _pd.isna(v):
                        return ""
                except Exception:
                    pass

                try:
                    if isinstance(v, numbers.Real) and not isinstance(v, bool):
                        fv = float(v)
                        if fv.is_integer():
                            return str(int(fv))
                        else:
                            return str(v)
                except Exception:
                    pass

                s = str(v).strip()
                if s.endswith(".0"):
                    core = s[:-2]
                    if core.isdigit():
                        return core
                return s
            except Exception:
                return "" 

        def get_col_val(names, fallback=""):
            for n in names:
                if n in row:
                    return row.get(n) or ""
            return fallback

        self.name_line.setText(clean_val(get_col_val(["CLIENTE", "Nombre", "NOMBRE", "name"], "")))
        self.number_line.setText(clean_val(get_col_val(["NUMERO", "Numero", "telefono", "TELEFONO"], "")))
        self.curp_line.setText(clean_val(get_col_val(["CURP"], "")))
        self.rfc_line.setText(clean_val(get_col_val(["RFC"], "")))
        self.nss_line.setText(clean_val(get_col_val(["NSS"], "")))
        self.email_line.setText(clean_val(get_col_val(["CORREO", "Email", "EMAIL", "email"], "")))

        wp = clean_val(get_col_val(["WORD", "Word", "word"], ""))
        pdfd = clean_val(get_col_val(["PDF", "Pdf", "pdf"], ""))

        self.word_path_label.setText(f"Dirección de Word: {wp}" if wp else "Dirección de Word: (ninguna)")
        self.pdf_dir_label.setText(f"Dirección de PDF: {pdfd}" if pdfd else "Dirección de PDF: (ninguna)")

        try:
            if getattr(self, "global_pdf_path", None):
                self._load_message_for_current_client_from_global()
        except Exception:
            pass

        self.excel.current_index = index
        self.status_label.setText(f"Fila {index+1} / {len(self.excel.df)}")

    def save_changes(self):
        if self.excel is None or self.excel.df is None:
            QMessageBox.warning(self, "Error", "Carga primero el Excel.")
            return

        self.btn_save_changes.setDisabled(True)
        try:
            idx = self.excel.current_index if self.excel.current_index is not None else 0

            def _extract_path_from_label(text, prefix):
                if not text:
                    return ""
                if text.startswith(prefix):
                    val = text[len(prefix):].strip()
                    if not val or val == "(ninguna)":
                        return ""
                    return os.path.abspath(val)
                if text.strip() == "(ninguna)":
                    return ""
                return os.path.abspath(text.strip())

            word_path = _extract_path_from_label(self.word_path_label.text() if hasattr(self, "word_path_label") else "", "Dirección de Word: ")
            pdf_path = _extract_path_from_label(self.pdf_dir_label.text() if hasattr(self, "pdf_dir_label") else "", "Dirección de PDF: ")

            mapping = {
                "CLIENTE": (self.name_line.text() if hasattr(self, "name_line") else ""),
                "CURP": (self.curp_line.text() if hasattr(self, "curp_line") else ""),
                "NSS": (self.nss_line.text() if hasattr(self, "nss_line") else ""),
                "CORREO": (self.email_line.text() if hasattr(self, "email_line") else ""),
                "RFC": (self.rfc_line.text() if hasattr(self, "rfc_line") else ""),
                "NUMERO": (self.number_line.text() if hasattr(self, "number_line") else ""),
                "WORD": word_path,
                "PDF": pdf_path
            }

            self.excel.ensure_columns(list(mapping.keys()))

            row_count = self.excel.row_count()
            if not isinstance(idx, int) or idx < 0 or idx >= row_count:
                self.excel.add_row(mapping)
                idx = self.excel.current_index
            else:
                self.excel.update_row(idx, mapping)

            try:
                self.excel.save()
            except PermissionError as pe:
                QMessageBox.warning(self, "Error guardando", f"PermissionError al guardar Excel:\n{pe}\n\nCierra el archivo si está abierto y vuelve a intentarlo.")
                return
            except Exception as e:
                QMessageBox.warning(self, "Error guardando", f"No se pudo guardar el Excel:\n{e}")
                return

            # refrescar UI
            self.status_label.setText("Cambios guardados en Excel.")
            self._refresh_client_list()
            self.show_row_index(idx)

        finally:
            self.btn_save_changes.setDisabled(False)

    def next_row(self):
        if self.excel:
            idx = (self.excel.current_index or 0) + 1
            if idx < len(self.excel.df):
                self.show_row_index(idx)

    def prev_row(self):
        if self.excel:
            idx = (self.excel.current_index or 0) - 1
            if idx >= 0:
                self.show_row_index(idx)

    def goto_row(self):
        if self.excel is None:
            return
        row_num, ok = QInputDialog.getInt(self, "Ir a fila", "Número de fila:", min=1, max=len(self.excel.df) if self.excel and self.excel.df is not None else 1)
        if ok:
            self.show_row_index(row_num - 1)

    # ------------------- Selenium -------------------
    def open_web_page(self):
        if not self.web.open_page("https://adodigital.imss.gob.mx/pti/inicio"):
            QMessageBox.warning(self, "Error", "No se pudo abrir la página.")
        else:
            self.show_captcha()

    def show_captcha(self):
        try:
            png = self.web.get_captcha_screenshot()
            pixmap = QPixmap(); pixmap.loadFromData(png)
            self.captcha_label.setPixmap(pixmap)
            self.captcha_label.setAlignment(Qt.AlignCenter)
            self.captcha_label.setScaledContents(True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo mostrar el captcha:\n{e}")

    def fill_form_in_web(self):
        try:
            if not self.download_folder:
                QMessageBox.warning(self, "Error", "Primero selecciona la carpeta de descargas. No se puede llenar el formulario sin una carpeta destino.")
                return 1

            if not self.web.driver:
                QMessageBox.warning(self, "Error", "Primero abre la página web.")
                return 1

            fields = {
                "curp": self.curp_line.text(),
                "rfc": self.rfc_line.text(),
                "nss": self.nss_line.text(),
                "email": self.email_line.text(),
                "emailConfirmacion": self.email_line.text(),
                "captcha": self.captcha_input.text()
            }

            for fid, val in fields.items():
                if fid == "rfc":
                    continue
                if not val.strip():
                    QMessageBox.warning(self, "Error", f"El campo '{fid}' está vacío.")
                    return 1

            res = self.web.fill_form_and_validate(fields)
            status = res.get("status")

            if status == "field_error":
                errs = res.get("errors", {})
                if errs:
                    first_msg = next(iter(errs.values()))
                    QMessageBox.warning(self, "Error en formulario", first_msg)
                else:
                    QMessageBox.warning(self, "Error en formulario", res.get("message", "Errores en campos."))
                return 1

            if status == "click_failed":
                QMessageBox.warning(self, "Error", res.get("message", "No se pudo continuar."))
                return 1

            if status == "form_error":
                QMessageBox.warning(self, "Error en Formulario", res.get("message", "Error al procesar formulario."))
                time.sleep(0.5)
                try:
                    self.show_captcha()
                    self.captcha_input.clear()
                except Exception:
                    pass
                return 1

            if status == "driver_error":
                QMessageBox.warning(self, "Error", res.get("message", "Error con el driver."))
                return 1

            return 0

        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo llenar el formulario:\n{e}")
            return 1
    
    def push_registration(self):
        try:
            res = self.web.complete_registration()
            status = res.get("status")
            message = res.get("message", "")
            details = res.get("details", [])

            if status == "ok":
                QMessageBox.information(self, "Registro", "Registro completado (o pasos realizados).")
                return 0
            elif status == "already_registered":
                QMessageBox.information(self, "Info", message or "Ya se había registrado previamente.")
                try:
                    self.show_captcha()
                    self.captcha_input.clear()
                except Exception:
                    pass
                return 1
            elif status == "no_action":
                QMessageBox.information(self, "Info", message or "No se encontraron acciones de registro.")
                try:
                    self.show_captcha()
                    self.captcha_input.clear()
                except Exception:
                    pass
                return 1
            else:
                msg = message or "No se completó el registro."
                if details:
                    msg += "\n\nDetalles:\n" + "\n".join(details)
                QMessageBox.warning(self, "Error registro", msg)
                try:
                    self.show_captcha()
                    self.captcha_input.clear()
                except Exception:
                    pass
                return 1
            return 0
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo completar el registro:\n{e}")
            return 1

    def download_pdf(self):
        web_res = self.web.initiate_pdf_downloads(click_count=2, wait_timeout=30)
        status = web_res.get("status")
        if status == "no_icons":
            QMessageBox.information(self, "Info", web_res.get("message", "No se encontraron iconos PDF en la página."))
            return
        if status == "wait_failed":
            QMessageBox.information(self, "Info", web_res.get("message", "Timeout esperando descargas."))
            return
        if status == "no_registred":
            QMessageBox.warning(self, "Info", web_res.get("message", "Error iniciando descargas."))
            return
        if status == "error":
            QMessageBox.warning(self, "Error", web_res.get("message", "Error iniciando descargas."))
            return

        if not self.download_folder:
            QMessageBox.warning(self, "Error", "No has seleccionado carpeta de descargas para mover los archivos.")
            return

        cliente = (self.name_line.text() if hasattr(self, "name_line") else "")
        subname = self._sanitize_for_filename(cliente) or "PDFs"

        proc = self.pdf_tools.move_and_process_temp(self.web.temp_download_dir, self.download_folder, subname, cliente)
        if proc.get("errors"):
            QMessageBox.warning(self, "Error procesando PDFs", "\n".join(proc.get("errors")))
            return

        final_paths = proc.get("final_paths", [])
        dest_folder = proc.get("dest_folder", "")
        pdf_to_save = proc.get("pdf_to_save", "")

        try:
            if self.excel is not None:
                idx = getattr(self.excel, "current_index", None)
                try:
                    idx = int(idx)
                except Exception:
                    idx = None
                updated_idx = self.excel.update_pdf_entry(index=idx, dest_folder=dest_folder, pdf_to_save=pdf_to_save)
                if updated_idx is not None:
                    try:
                        self.pdf_dir_label.setText(f"Dirección de PDF: {pdf_to_save}" if pdf_to_save else "Dirección de PDF: (ninguna)")
                        self._refresh_client_list()
                        self.show_row_index(int(updated_idx))
                    except Exception:
                        pass
                else:
                    QMessageBox.warning(self, "Aviso", "No se pudo guardar la ruta en Excel tras mover PDFs.")
        except Exception:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", "Error guardando en Excel después de mover PDFs.")

        try:
            self.web.click_button("salir")
        except Exception:
            pass

        QMessageBox.information(self, "Info", "Proceso de descarga finalizado.")

    def registration(self):
        if not self.fill_form_in_web(): 
            if not self.push_registration():
                self.download_pdf()
        self.show_captcha()

    def get_pdf(self):
        if not self.fill_form_in_web():
            self.download_pdf()
        self.show_captcha()

    # ------------------- PDFs -------------------
    def move_downloaded_pdf(self):
        if not self.download_folder:
            QMessageBox.warning(self, "Error", "Primero selecciona la carpeta de descargas.")
            return
        try:
            cliente = (self.name_line.text() if hasattr(self, "name_line") else "")
            subname = self._sanitize_for_filename(cliente) or "PDFs"

            proc = self.pdf_tools.move_and_process_temp(self.web.temp_download_dir, self.download_folder, subname, cliente)
            if proc.get("errors"):
                QMessageBox.warning(self, "Error procesando PDFs", "\n".join(proc.get("errors")))
                return

            final_paths = proc.get("final_paths", [])
            dest_folder = proc.get("dest_folder", "")
            pdf_to_save = proc.get("pdf_to_save", "")

            if self.excel is not None:
                idx = getattr(self.excel, "current_index", None)
                try:
                    idx = int(idx)
                except Exception:
                    idx = None
                updated_idx = self.excel.update_pdf_entry(index=idx, dest_folder=dest_folder, pdf_to_save=pdf_to_save)
                if updated_idx is not None:
                    try:
                        if pdf_to_save:
                            self.pdf_dir_label.setText(f"Dirección de PDF: {pdf_to_save}")
                        else:
                            self.pdf_dir_label.setText("Dirección de PDF: (ninguna)")
                        self._refresh_client_list()
                        self.show_row_index(int(updated_idx))
                    except Exception:
                        pass
                else:
                    QMessageBox.warning(self, "Aviso", "No se pudo guardar la ruta en Excel tras mover PDFs.")

            QMessageBox.information(self, "Info", f"{len(final_paths)} PDFs procesados.")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo mover/procesar los PDFs:\n{e}")

    def select_global_pdf_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF global (.pdf)", "", "Archivos PDF (*.pdf)")
        if not path:
            return
        self.global_pdf_path = os.path.abspath(path)
        try:
            self.global_pdf_label.setText(f"PDF global: {os.path.basename(self.global_pdf_path)}")
        except Exception:
            self.global_pdf_label.setText(f"PDF global: {self.global_pdf_path}")
        try:
            self._load_message_for_current_client_from_global()
        except Exception:
            pass

    def _load_message_for_current_client_from_global(self):
        try:
            if not getattr(self, "global_pdf_path", None):
                return
            if not os.path.exists(self.global_pdf_path):
                return

            client = (self.name_line.text() if hasattr(self, "name_line") else "").strip()
            if not client:
                return

            res = self.pdf_tools.find_message_for_client_in_pdf(self.global_pdf_path, client, fuzzy=True)
            if res.get("found"):
                self.word_preview.setPlainText(res.get("text", ""))
                self.current_pdf_location = {
                    "pdf_path": os.path.abspath(self.global_pdf_path),
                    "page_idx": int(res.get("page_idx")),
                    "snippet": res.get("snippet")
                }
            else:
                self.word_preview.setPlainText("(No se encontró mensaje para este cliente en el PDF global. Edita aquí el mensaje.)")
                self.current_pdf_location = None

            if res.get("errors"):
                print("[PDF search errors]", res["errors"])

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.current_pdf_location = None

    def reload_message_for_current_client(self):
        try:
            self._load_message_for_current_client_from_global()
            QMessageBox.information(self, "Recargar mensaje", "Se intentó recargar el mensaje desde el PDF global.")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo recargar mensaje:\n{e}")

    # ------------------- Carpeta descargas -------------------
    def select_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de descargas")
        if folder:
            self.download_folder = folder
            self.web.set_download_folder(folder)
            QMessageBox.information(self, "Carpeta seleccionada", f"Descargas se guardarán en:\n{folder}")
            self.selected_download_label.setText(f"Carpeta final: {self.download_folder}")

    # ----------------- Panel 1 helpers: abrir pdf dir / open word -----------------
    def open_pdf_dir(self):
        if self.excel is None or self.excel.df is None:
            QMessageBox.warning(self, "Error", "Carga primero el Excel.")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo PDF (.pdf)", "", "Archivos PDF (*.pdf)")
        if not path:
            return

        try:
            idx = getattr(self.excel, "current_index", None)
            try:
                idx = int(idx)
            except Exception:
                idx = None

            updated_idx = None
            try:
                updated_idx = self.excel.update_pdf_entry(index=idx, dest_folder=None, pdf_to_save=path)
            except Exception:
                traceback.print_exc()
                updated_idx = None

            if updated_idx is None:
                try:
                    self.excel.ensure_columns(["PDF"])
                    if idx is None or not (0 <= idx < self.excel.row_count()):
                        idx = self.excel.add_row({})
                    row_label = self.excel.df.index[idx]
                    self.excel.df.at[row_label, "PDF"] = os.path.abspath(path)
                    if hasattr(self.excel, "save"):
                        self.excel.save()
                    else:
                        self.excel.save_excel_atomic()
                    updated_idx = int(idx)
                except Exception:
                    traceback.print_exc()
                    updated_idx = None

            if updated_idx is not None:
                self.pdf_dir_label.setText(f"Dirección de PDF: {os.path.abspath(path)}")
                self.status_label.setText("Ruta PDF guardada en Excel.")
                self._refresh_client_list()
                try:
                    self.show_row_index(int(updated_idx))
                except Exception:
                    pass
            else:
                QMessageBox.warning(self, "Error", "No se pudo guardar la ruta PDF en el Excel.")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo guardar ruta PDF:\n{e}")

    def open_word_file(self):
        if self.excel is None or self.excel.df is None:
            QMessageBox.warning(self, "Error", "Carga primero el Excel.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo Word (.docx)", "", "Archivos Word (*.docx)")
        if not path:
            return
        try:
            idx = self.excel.current_index or 0
            row_label = self.excel.df.index[idx]
            col = None
            for cand in ["WORD", "Word", "word"]:
                if cand in self.excel.df.columns:
                    col = cand
                    break
            if not col:
                self.excel.df["WORD"] = ""
                col = "WORD"
            self.excel.df.at[row_label, col] = os.path.abspath(path)
            try:
                if hasattr(self.excel, "save"):
                    self.excel.save()
                else:
                    self.excel.save_excel_atomic()
            except Exception:
                pass
            self.word_path_label.setText(f"Dirección de Word: {path}")
            self._preview_word_file(path)
            self.status_label.setText("Ruta Word guardada en Excel.")
            self._refresh_client_list()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo guardar ruta WORD:\n{e}")

    def _preview_word_file(self, path):
        try:
            from docx import Document
        except Exception:
            self.word_preview.setPlainText(f"(python-docx no instalado)\nRuta: {path}")
            return
        try:
            if not os.path.exists(path):
                self.word_preview.setPlainText(f"Archivo no existe: {path}")
                return
            doc = Document(path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip() != ""]
            text = "\n\n".join(paragraphs)
            max_len = 200000
            if len(text) > max_len:
                text = text[:max_len] + "\n\n(...texto truncado...)"
            self.word_preview.setPlainText(text)
        except Exception as e:
            traceback.print_exc()
            self.word_preview.setPlainText(f"No se pudo previsualizar .docx: {e}")

    def _sanitize_for_filename(self, name: str) -> str:
        if not name:
            return ""
        invalid = '<>:"/\\|?*\n\r\t'
        clean = ''.join(ch for ch in name if ch not in invalid)
        clean = clean.strip()
        while "  " in clean:
            clean = clean.replace("  ", " ")
        return clean[:200]

    # ----------------- Panel 3: Envío / Preview -----------------
    def send_message(self):
        try:
            numero = (self.number_line.text() if hasattr(self, "number_line") else "").strip()
            if not numero:
                QMessageBox.warning(self, "Error", "No hay número para el cliente.")
                return
            num = "".join(ch for ch in numero if ch.isdigit() or ch == '+')

            message_text = self.word_preview.toPlainText().strip()
            if not message_text:
                QMessageBox.warning(self, "Error", "El mensaje está vacío.")
                return
            pdf_path = ""
            try:
                if self.pdf_dir_label and self.pdf_dir_label.text().startswith("Dirección de PDF:"):
                    p = self.pdf_dir_label.text()[len("Dirección de PDF:"):].strip()
                    if p and p != "(ninguna)":
                        pdf_path = p
            except Exception:
                pass
            if not pdf_path and self.excel:
                try:
                    row = self.excel.get_row(self.excel.current_index)
                    for cand in ("PDF", "Pdf", "pdf", "CarpetaPDF", "CarpetaPdf", "carpetapdf"):
                        if row.get(cand):
                            pdf_path = row.get(cand)
                            break
                except Exception:
                    pass
            if not pdf_path:
                QMessageBox.warning(self, "Error", "No se encontró ruta al PDF en la fila.")
                return
            pdf_path = os.path.abspath(pdf_path)
            if not os.path.exists(pdf_path):
                QMessageBox.warning(self, "Error", f"No existe el PDF: {pdf_path}")
                return

            ok = QMessageBox.question(self, "Confirmar envío",
                                    f"Enviar mensaje + PDF a {self.name_line.text()} ({num})?",
                                    QMessageBox.Yes | QMessageBox.No)
            if ok != QMessageBox.Yes:
                return

            if not self._is_whatsapp_session_active_ui():
                QMessageBox.information(self, "WhatsApp Web", "Parece que WhatsApp Web no está activo en el navegador. Pulsa 'Abrir WhatsApp Web' y escanea el QR si es necesario (sólo la primera vez).")
                return

            res = self.whatsapp.send_message_with_pdf(phone_number=num, message=message_text, pdf_path=pdf_path)
            st = res.get("status")
            if st == "ok":
                try:
                    idx = getattr(self.excel, "current_index", None)
                    try:
                        idx = int(idx)
                    except Exception:
                        idx = None
                    save_map = {}
                    if getattr(self, "current_pdf_location", None):
                        save_map["WORD"] = self.current_pdf_location.get("pdf_path", "")
                        save_map["WORD_LOC"] = f"page_idx:{self.current_pdf_location.get('page_idx')} | snippet:{self.current_pdf_location.get('snippet')}"
                    elif getattr(self, "global_pdf_path", None):
                        save_map["WORD"] = os.path.abspath(self.global_pdf_path)
                    from datetime import datetime
                    save_map["UltimaActualizacion"] = datetime.now().isoformat(sep=" ", timespec="seconds")
                    if self.excel:
                        if isinstance(idx, int) and 0 <= idx < self.excel.row_count():
                            self.excel.update_row(idx, save_map)
                        else:
                            self.excel.add_row(save_map)
                        try:
                            self.excel.save()
                        except Exception:
                            pass
                except Exception:
                    traceback.print_exc()

                QMessageBox.information(self, "Envío", "Mensaje y PDF enviados (si no hubo errores en WhatsApp Web).")
                self.status_label.setText("Envío: OK.")
                return
            elif st == "needs_qr":
                qr = res.get("qr_path") or "whatsapp_qr.png"
                if os.path.exists(qr):
                    try:
                        p = QPixmap(qr)
                        self.captcha_label.setPixmap(p)
                        self.captcha_label.setScaledContents(True)
                        self.captcha_label.setAlignment(Qt.AlignCenter)
                    except Exception:
                        pass
                QMessageBox.information(self, "WhatsApp Web", "La sesión no está activa. Escanea el QR mostrado en la App y reintenta el envío.")
                self.status_label.setText("WhatsApp Web: necesita QR.")
                return
            else:
                msg = res.get("message", "Error desconocido al enviar por WhatsApp.")
                QMessageBox.warning(self, "Error envío", msg)
                self.status_label.setText(f"Envío: error ({msg})")
                return

        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo enviar el mensaje:\n{e}")
            self.status_label.setText("Envío: excepción.")

    def send_message_quiet(self):
        try:
            numero = (self.number_line.text() if hasattr(self, "number_line") else "").strip()
            num = "".join(ch for ch in numero if ch.isdigit() or ch == '+')
            
            if not num or len(num) < 3:
                self.status_label.setStyleSheet("color:#c62828;")
                self.status_label.setText("Error: número inválido.")
                return {"status":"error","message":"numero invalido"}

            message_text = self.word_preview.toPlainText().strip()
            if not message_text:
                try:
                    self._load_message_for_current_client_from_global()
                    message_text = self.word_preview.toPlainText().strip()
                except Exception:
                    pass
            if not message_text:
                self.status_label.setStyleSheet("color:#c62828;")
                self.status_label.setText("Error: mensaje vacío.")
                return {"status":"error","message":"mensaje vacio"}

            pdf_path = ""
            try:
                if self.pdf_dir_label and self.pdf_dir_label.text().startswith("Dirección de PDF:"):
                    p = self.pdf_dir_label.text()[len("Dirección de PDF:"):].strip()
                    if p and p != "(ninguna)":
                        pdf_path = p
            except Exception:
                pass
            if not pdf_path and self.excel:
                try:
                    row = self.excel.get_row(self.excel.current_index)
                    for cand in ("PDF", "Pdf", "pdf", "CarpetaPDF"):
                        if row.get(cand):
                            pdf_path = row.get(cand)
                            break
                except Exception:
                    pass
            if not pdf_path or not os.path.exists(os.path.abspath(pdf_path)):
                self.status_label.setStyleSheet("color:#c62828;")
                self.status_label.setText("Error: PDF no encontrado.")
                return {"status":"error","message":"pdf no encontrado"}

            if not self._is_whatsapp_session_active_ui():
                self.status_label.setStyleSheet("color:#d08500;")
                self.status_label.setText("WhatsApp Web inactivo (escanea QR).")
                return {"status":"needs_qr","message":"whatsapp inactivo"}

            res = self.whatsapp.send_message_with_pdf(
                phone_number=num,
                message=message_text,
                pdf_path=os.path.abspath(pdf_path)
            )
            st = res.get("status")

            if st == "ok":
                try:
                    idx = getattr(self.excel, "current_index", None)
                    try:
                        idx = int(idx)
                    except Exception:
                        idx = None
                    save_map = {}
                    if getattr(self, "current_pdf_location", None):
                        save_map["WORD"] = self.current_pdf_location.get("pdf_path", "")
                        save_map["WORD_LOC"] = f"page_idx:{self.current_pdf_location.get('page_idx')} | snippet:{self.current_pdf_location.get('snippet')}"
                    elif getattr(self, "global_pdf_path", None):
                        save_map["WORD"] = os.path.abspath(self.global_pdf_path)
                    from datetime import datetime as _dt
                    save_map["UltimaActualizacion"] = _dt.now().isoformat(sep=" ", timespec="seconds")
                    if self.excel:
                        self.excel.ensure_columns(["WORD","WORD_LOC","UltimaActualizacion"])
                        if isinstance(idx, int) and 0 <= idx < self.excel.row_count():
                            self.excel.update_row(idx, save_map)
                        else:
                            self.excel.add_row(save_map)
                        try:
                            self.excel.save()
                        except Exception:
                            pass
                except Exception:
                    traceback.print_exc()

                self.status_label.setStyleSheet("color:green;")
                self.status_label.setText("Envío OK.")
                return res

            # errores
            self.status_label.setStyleSheet("color:#c62828;")
            self.status_label.setText(f"Error envío: {res.get('message','desconocido')}")
            return res

        except Exception as e:
            traceback.print_exc()
            self.status_label.setStyleSheet("color:#c62828;")
            self.status_label.setText(f"Excepción en envío: {e}")
            return {"status":"error","message":str(e)}

    def send_range(self):
        if self.excel is None or self.excel.df is None:
            self.status_label.setStyleSheet("color:#c62828;")
            self.status_label.setText("Carga primero el Excel.")
            return

        try:
            l = int(self.range_from.text().strip()) - 1
            r = int(self.range_to.text().strip()) - 1
        except Exception:
            self.status_label.setStyleSheet("color:#c62828;")
            self.status_label.setText("Rango inválido. Usa números en 'Desde' y 'Hasta'.")
            return

        n = len(self.excel.df)
        l = max(0, min(n-1, l))
        r = max(0, min(n-1, r))
        if l > r:
            l, r = r, l

        if not self._is_whatsapp_session_active_ui():
            self.status_label.setStyleSheet("color:#d08500;")
            self.status_label.setText("WhatsApp Web inactivo (escanea QR y reintenta).")
            return

        self.btn_send_range.setDisabled(True)
        self.status_label.setStyleSheet("color:green;")
        self.status_label.setText(f"Iniciando envío {l+1}–{r+1}...")

        ok, fail = 0, 0
        try:
            for i in range(l, r+1):
                try:
                    self.show_row_index(i)
                    QApplication.processEvents()
                    time.sleep(0.5)
                    res = self.send_message_quiet() 
                    if res.get("status") == "ok":
                        ok += 1
                    else:
                        fail += 1
                    self.status_label.setText(f"Progreso {i-l+1}/{r-l+1} (ok:{ok} err:{fail})")
                    QApplication.processEvents()
                    start_time = time.time()
                    while time.time() - start_time < 3:
                        remaining = int(3 - (time.time() - start_time))
                        time.sleep(0.1)
                
                    
                except Exception as e:
                    fail += 1
                    print(f"[Enviar rango] Fila {i+1}: {e}")
            self.status_label.setStyleSheet("color:green;" if fail == 0 else "color:#d08500;")
            self.status_label.setText(f"Rango terminado. Éxitos: {ok} • Fallos: {fail}")
        finally:
            self.btn_send_range.setDisabled(False)

    def _ui_open_whatsapp(self):
        try:
            res = self.whatsapp.open_whatsapp(wait_for_qr=3)
            st = res.get("status")
            if st == "ok":
                QMessageBox.information(self, "WhatsApp Web", res.get("message", "WhatsApp Web listo."))
                self.status_label.setText("WhatsApp Web: sesión activa.")
                try:
                    self.captcha_label.clear()
                except Exception:
                    pass
                return
            elif st == "needs_qr":
                qr_path = res.get("qr_path") or "whatsapp_qr.png"
                if os.path.exists(qr_path):
                    try:
                        pix = QPixmap(qr_path)
                        self.captcha_label.setPixmap(pix)
                        self.captcha_label.setScaledContents(True)
                        self.captcha_label.setAlignment(Qt.AlignCenter)
                    except Exception:
                        pass
                QMessageBox.information(self, "WhatsApp Web - QR", "Escanea el QR con tu teléfono. Luego pulsa 'Abrir WhatsApp Web' nuevamente o intenta enviar el mensaje.")
                self.status_label.setText("WhatsApp Web: necesita escanear QR.")
                return
            else:
                QMessageBox.warning(self, "WhatsApp Web", res.get("message", "No se pudo abrir WhatsApp Web."))
                self.status_label.setText("WhatsApp Web: error al abrir.")
                return
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo abrir WhatsApp Web:\n{e}")

    def _is_whatsapp_session_active_ui(self) -> bool:
        try:
            wm = getattr(self, "whatsapp", None)
            if not wm or not getattr(wm, "driver", None):
                return False
            drv = wm.driver
            try:
                cur = drv.current_url or ""
            except Exception:
                cur = ""
            if "web.whatsapp.com" not in cur:
                return False
            try:
                if drv.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']"):
                    return True
                if drv.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']"):
                    return True
                if drv.find_elements(By.CSS_SELECTOR, "div[data-testid='conversation-panel']"):
                    return True
            except Exception:
                return False
            return False
        except Exception:
            return False

    def whatsapp_debug_info(self):
        try:
            wm = getattr(self, "whatsapp", None)
            if not wm or not getattr(wm, "driver", None):
                print("WhatsApp driver: None")
                return
            d = wm.driver
            print("=== WhatsApp debug ===")
            try:
                print("current_url:", d.current_url)
            except Exception as e:
                print("current_url: (error)", e)
            try:
                print("title:", d.title)
            except Exception:
                pass
            try:
                def count(sel):
                    try:
                        return len(d.find_elements(By.CSS_SELECTOR, sel))
                    except Exception:
                        return "err"
                checks = {
                    "search(data-tab=3)": "div[contenteditable='true'][data-tab='3']",
                    "chat_input(data-tab=10)": "div[contenteditable='true'][data-tab='10']",
                    "conversation_panel": "div[data-testid='conversation-panel']",
                    "pane_side": "div[data-testid='pane-side']",
                    "file_input": "input[type='file']",
                    "attach_btn_plus": "span[data-icon='plus-rounded']",
                    "attach_btn_clip": "span[data-testid='clip']",
                }
                for k, sel in checks.items():
                    print(f"{k}: {count(sel)} (sel: {sel})")
            except Exception as e:
                print("element counts error:", e)

            try:
                c = d.get_cookies()
                print("cookies_count:", len(c))
                if len(c) <= 20:
                    print("cookies:", c)
                else:
                    print("cookies (first 10):", c[:10])
            except Exception as e:
                print("cookies error:", e)

            try:
                keys = d.execute_script("return Object.keys(window.localStorage || {});")
                print("localStorage keys:", keys)
            except Exception as e:
                print("localStorage error:", e)

            try:
                ps = d.page_source or ""
                print("page_source length:", len(ps))
                print("page_source snippet:", ps[:2000].replace("\n", " ")[:1000])
            except Exception:
                pass

            print("=== end debug ===")
        except Exception as ex:
            print("whatsapp_debug_info exception:", ex)
  
    # ----------------- Utilidades varias -----------------
    def _client_list_clicked(self, item):
        try:
            text = item.text()
            num = int(text.split(" - ", 1)[0])
            self.show_row_index(num - 1)
        except Exception:
            pass

    def _refresh_client_list(self):
        if self.excel is None or self.excel.df is None:
            return
        cols = list(self.excel.df.columns)
        name_col = None
        for cand in ["Nombre", "NOMBRE", "name"]:
            if cand in cols:
                name_col = cand
                break
        for i in range(len(self.excel.df)):
            row = self.excel.get_row(i)
            name = str(row.get(name_col, '') or '')

    def new_client(self):
        if self.excel is None:
            QMessageBox.warning(self, "Error", "Carga primero el Excel.")
            return

        try:
            if self.excel.df is None:
                cols = ["Nombre", "NUMERO", "CURP", "RFC", "NSS", "CORREO", "WORD", "CarpetaPDF"]
                self.excel.df = pd.DataFrame(columns=cols)

            if len(self.excel.df.columns) == 0:
                default_cols = ["Nombre", "NUMERO", "CURP", "RFC", "NSS", "CORREO", "WORD", "CarpetaPDF"]
                self.excel.df = pd.DataFrame(columns=default_cols)

            cols = list(self.excel.df.columns)
            new_row = {c: "" for c in cols}

            self.excel.df = pd.concat([self.excel.df, pd.DataFrame([new_row])], ignore_index=True)

            try:
                if hasattr(self.excel, "save"):
                    self.excel.save()
                else:
                    self.excel.save_excel_atomic()
            except Exception:
                traceback.print_exc()
                self.status_label.setText("Aviso: no se pudo guardar Excel en disco (revisar permisos).")

            new_index = len(self.excel.df) - 1
            self.show_row_index(new_index)
            self._refresh_client_list()
            self.status_label.setText("Nuevo cliente creado.")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"No se pudo crear nuevo cliente:\n{e}")

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = ExcelInterface()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        excepcion_no_manejada(type(e), e, e.__traceback__)

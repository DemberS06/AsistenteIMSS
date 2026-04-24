# interfaz.py
from __future__ import annotations

import os
import sys
import time
import traceback

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox,
    QFileDialog, QInputDialog, QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from config import DATA_DIR
from models.trabajador import Trabajador
from models.mensaje import Mensaje
from workflow.imss_ti import IMSSTiWorkflow


# ──────────────────────────────────────────────────────────────
# Log de errores no manejados
# ──────────────────────────────────────────────────────────────

def _excepcion_no_manejada(exc_type, exc_value, exc_tb):
    texto = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        log_path = os.path.join(DATA_DIR, "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(texto + "\n")
    except Exception:
        pass
    try:
        QMessageBox.critical(
            None, "Error no manejado",
            f"Ocurrió un error:\n{exc_value}\n\n"
            f"Revisa el log en:\n{os.path.join(DATA_DIR, 'error.log')}"
        )
    except Exception:
        print("Error crítico:\n", texto)
    sys.exit(1)


sys.excepthook = _excepcion_no_manejada


# ──────────────────────────────────────────────────────────────
# Ventana principal
# ──────────────────────────────────────────────────────────────

class Interfaz(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente IMSS")
        self.setGeometry(150, 80, 1200, 720)

        self.workflow = IMSSTiWorkflow(DATA_DIR)

        # Estado de sesión (no va al Excel)
        self._global_pdf_path: str = ""   # PDF global de mensajes seleccionado por el usuario

        main_layout = QHBoxLayout()
        main_layout.addWidget(self._build_panel_cliente(),   3)
        main_layout.addWidget(self._build_panel_registro(),  2)
        main_layout.addWidget(self._build_panel_mensaje(),   3)

        outer = QVBoxLayout()
        outer.addLayout(main_layout)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: green;")
        outer.addWidget(self.status_label)
        self.setLayout(outer)

    # ──────────────────────────────────────────────────────────
    # Constructores de paneles
    # ──────────────────────────────────────────────────────────

    def _build_panel_cliente(self) -> QGroupBox:
        panel = QGroupBox("Cliente")
        layout = QVBoxLayout()

        # Abrir Excel / Seleccionar PDF del cliente
        btn_row = QHBoxLayout()
        self.btn_open_excel = QPushButton("Abrir Excel")
        self.btn_open_excel.clicked.connect(self._load_excel)
        self.btn_select_pdf = QPushButton("Seleccionar PDF")
        self.btn_select_pdf.clicked.connect(self._select_client_pdf)
        btn_row.addWidget(self.btn_open_excel)
        btn_row.addWidget(self.btn_select_pdf)
        layout.addLayout(btn_row)

        # Campos editables
        self.name_line   = QLineEdit(); self.name_line.setPlaceholderText("Nombre del cliente")
        self.number_line = QLineEdit(); self.number_line.setPlaceholderText("Número de teléfono")
        self.curp_line   = QLineEdit(); self.curp_line.setPlaceholderText("CURP")
        self.rfc_line    = QLineEdit(); self.rfc_line.setPlaceholderText("RFC")
        self.nss_line    = QLineEdit(); self.nss_line.setPlaceholderText("NSS")
        self.email_line  = QLineEdit(); self.email_line.setPlaceholderText("Correo")
        for w in [self.name_line, self.number_line, self.curp_line,
                  self.rfc_line, self.nss_line, self.email_line]:
            layout.addWidget(w)

        # Etiqueta PDF del cliente
        self.pdf_dir_label = QLabel("PDF del cliente: (ninguno)")
        self.pdf_dir_label.setWordWrap(True)
        layout.addWidget(self.pdf_dir_label)

        # Guardar / Nuevo
        save_row = QHBoxLayout()
        self.btn_save = QPushButton("Guardar cambios")
        self.btn_save.clicked.connect(self._save_changes)
        self.btn_new  = QPushButton("Nuevo cliente")
        self.btn_new.clicked.connect(self._new_client)
        save_row.addWidget(self.btn_save)
        save_row.addWidget(self.btn_new)
        layout.addLayout(save_row)

        # Navegación
        nav_row = QHBoxLayout()
        self.btn_prev = QPushButton("← Anterior")
        self.btn_prev.clicked.connect(self._prev_row)
        self.btn_next = QPushButton("Siguiente →")
        self.btn_next.clicked.connect(self._next_row)
        self.btn_goto = QPushButton("Ir al cliente X")
        self.btn_goto.clicked.connect(self._goto_row)
        nav_row.addWidget(self.btn_prev)
        nav_row.addWidget(self.btn_next)
        nav_row.addWidget(self.btn_goto)
        layout.addLayout(nav_row)

        panel.setLayout(layout)
        return panel

    def _build_panel_registro(self) -> QGroupBox:
        panel = QGroupBox("Registro IMSS")
        layout = QVBoxLayout()

        # Carpeta de descarga
        self.btn_select_folder = QPushButton("Seleccionar carpeta de descarga")
        self.btn_select_folder.clicked.connect(self._select_download_folder)
        layout.addWidget(self.btn_select_folder)

        self.folder_label = QLabel("Carpeta: (ninguna)")
        self.folder_label.setWordWrap(True)
        layout.addWidget(self.folder_label)

        # Captcha
        self.captcha_label = QLabel("Captcha aquí")
        self.captcha_label.setAlignment(Qt.AlignCenter)
        self.captcha_label.setFixedSize(440, 80)
        self.captcha_label.setStyleSheet("border: 1px solid black;")
        layout.addWidget(self.captcha_label)

        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText("Escribe el captcha")
        layout.addWidget(self.captcha_input)

        # Registro / Descarga
        reg_row = QHBoxLayout()
        self.btn_register = QPushButton("Registrar cliente")
        self.btn_register.clicked.connect(self._register_client)
        self.btn_download = QPushButton("Descargar PDF")
        self.btn_download.clicked.connect(self._download_pdf)
        reg_row.addWidget(self.btn_register)
        reg_row.addWidget(self.btn_download)
        layout.addLayout(reg_row)

        # Página / Captcha
        page_row = QHBoxLayout()
        self.btn_open_page    = QPushButton("Abrir página")
        self.btn_open_page.clicked.connect(self._open_imss_page)
        self.btn_show_captcha = QPushButton("Mostrar captcha")
        self.btn_show_captcha.clicked.connect(self._show_captcha)
        page_row.addWidget(self.btn_open_page)
        page_row.addWidget(self.btn_show_captcha)
        layout.addLayout(page_row)

        panel.setLayout(layout)
        return panel

    def _build_panel_mensaje(self) -> QGroupBox:
        panel = QGroupBox("Mensaje WhatsApp")
        layout = QVBoxLayout()

        # PDF global de mensajes
        self.btn_select_global_pdf = QPushButton("Seleccionar PDF de mensajes")
        self.btn_select_global_pdf.clicked.connect(self._select_global_pdf)
        layout.addWidget(self.btn_select_global_pdf)

        self.global_pdf_label = QLabel("PDF de mensajes: (ninguno)")
        self.global_pdf_label.setWordWrap(True)
        layout.addWidget(self.global_pdf_label)

        # Preview del mensaje (solo lectura, igual que el código viejo)
        self.word_preview = QTextEdit()
        self.word_preview.setReadOnly(True)
        self.word_preview.setPlaceholderText("Aquí se mostrará el texto del mensaje del cliente.")
        layout.addWidget(self.word_preview)

        # Enviar
        self.btn_send = QPushButton("Enviar mensaje")
        self.btn_send.clicked.connect(self._send_message)
        layout.addWidget(self.btn_send)

        self.btn_open_whatsapp = QPushButton("Abrir WhatsApp Web")
        self.btn_open_whatsapp.clicked.connect(self._open_whatsapp)
        layout.addWidget(self.btn_open_whatsapp)

        # Rango
        range_row = QHBoxLayout()
        self.range_from = QLineEdit(); self.range_from.setPlaceholderText("Desde")
        self.range_to   = QLineEdit(); self.range_to.setPlaceholderText("Hasta")
        range_row.addWidget(self.range_from)
        range_row.addWidget(self.range_to)
        layout.addLayout(range_row)

        self.btn_send_range = QPushButton("Enviar en rango")
        self.btn_send_range.clicked.connect(self._send_range)
        layout.addWidget(self.btn_send_range)

        panel.setLayout(layout)
        return panel

    # ──────────────────────────────────────────────────────────
    # Panel 1 — Cliente
    # ──────────────────────────────────────────────────────────

    def _load_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Excel", "", "Excel (*.xlsx *.xls)"
        )
        if not path:
            return
        try:
            trabajador = self.workflow.load_excel(path)
            self._fill_form(trabajador)
            self._set_status(f"Excel cargado: {os.path.basename(path)}")
        except Exception as e:
            self._show_error("Error cargando Excel", e)

    def _save_changes(self):
        self.btn_save.setDisabled(True)
        try:
            self.workflow.save_current_client(self._collect_form())
            self._set_status("Cambios guardados.")
            # Refrescar para mostrar datos limpios del Excel
            self._fill_form(self.workflow.get_current_client())
        except PermissionError as e:
            QMessageBox.warning(
                self, "Error guardando",
                f"No se pudo guardar el Excel (¿está abierto?):\n{e}"
            )
        except Exception as e:
            self._show_error("Error guardando cambios", e)
        finally:
            self.btn_save.setDisabled(False)

    def _new_client(self):
        try:
            trabajador = self.workflow.create_new_client()
            self._fill_form(trabajador)
            self._set_status("Nuevo cliente creado.")
        except Exception as e:
            self._show_error("Error creando cliente", e)

    def _prev_row(self):
        try:
            self._fill_form(self.workflow.go_previous())
            self._auto_load_message()
        except Exception as e:
            self._show_error("Error", e)

    def _next_row(self):
        try:
            self._fill_form(self.workflow.go_next())
            self._auto_load_message()
        except Exception as e:
            self._show_error("Error", e)

    def _goto_row(self):
        total = self.workflow.row_count() if self.workflow.excel else 1
        index, ok = QInputDialog.getInt(
            self, "Ir a cliente", "Número de fila:", min=1, max=total
        )
        if ok:
            try:
                self._fill_form(self.workflow.go_to(index - 1))
                self._auto_load_message()
            except Exception as e:
                self._show_error("Error", e)

    def _select_client_pdf(self):
        """Permite seleccionar manualmente el PDF del cliente y lo guarda en el Excel."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar PDF del cliente", "", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            abs_path = os.path.abspath(path)
            self.workflow.update_field("PDF", abs_path)
            self.pdf_dir_label.setText(f"PDF del cliente: {abs_path}")
            self._set_status("Ruta PDF guardada en Excel.")
        except Exception as e:
            self._show_error("Error guardando ruta PDF", e)

    def _select_download_folder(self):
        """Selecciona la carpeta de descarga y la guarda en CARPETAPDF del cliente actual."""
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de descarga")
        if not folder:
            return
        try:
            self.workflow.update_field("CARPETAPDF", folder)
            self.folder_label.setText(f"Carpeta: {folder}")
            self._set_status("Carpeta de descarga guardada.")
        except Exception as e:
            self._show_error("Error guardando carpeta", e)

    # ──────────────────────────────────────────────────────────
    # Panel 2 — Registro IMSS
    # ──────────────────────────────────────────────────────────

    def _open_imss_page(self):
        try:
            self.workflow.open_imss_page()
            self._show_captcha()
            self._set_status("Página IMSS abierta.")
        except Exception as e:
            self._show_error("Error abriendo página", e)

    def _show_captcha(self):
        try:
            data = self.workflow.get_captcha()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.captcha_label.setPixmap(pixmap)
            self.captcha_label.setScaledContents(True)
            self.captcha_label.setAlignment(Qt.AlignCenter)
        except Exception as e:
            self._show_error("Error mostrando captcha", e)

    def _register_client(self):
        captcha = self.captcha_input.text().strip()
        if not captcha:
            QMessageBox.warning(self, "Captcha requerido", "Escribe el captcha antes de registrar.")
            return
        try:
            pdf = self.workflow.register_current_client(captcha)
            self.pdf_dir_label.setText(f"PDF del cliente: {pdf}")
            self.captcha_input.clear()
            self._show_captcha()
            self._set_status("Cliente registrado y PDF descargado.")
        except Exception as e:
            self.captcha_input.clear()
            try:
                self._show_captcha()
            except Exception:
                pass
            self._show_error("Error en registro", e)

    def _download_pdf(self):
        captcha = self.captcha_input.text().strip()
        if not captcha:
            QMessageBox.warning(self, "Captcha requerido", "Escribe el captcha antes de descargar.")
            return
        try:
            pdf = self.workflow.download_pdf_current_client(captcha)
            self.pdf_dir_label.setText(f"PDF del cliente: {pdf}")
            self.captcha_input.clear()
            self._show_captcha()
            self._set_status("PDF descargado.")
        except Exception as e:
            self.captcha_input.clear()
            try:
                self._show_captcha()
            except Exception:
                pass
            self._show_error("Error descargando PDF", e)

    # ──────────────────────────────────────────────────────────
    # Panel 3 — Mensaje / WhatsApp
    # ──────────────────────────────────────────────────────────

    def _select_global_pdf(self):
        """Selecciona el PDF global de mensajes (solo sesión, no va al Excel)."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar PDF de mensajes", "", "PDF (*.pdf)"
        )
        if not path:
            return
        self._global_pdf_path = os.path.abspath(path)
        self.global_pdf_label.setText(
            f"PDF de mensajes: {os.path.basename(self._global_pdf_path)}"
        )
        self._auto_load_message()

    def _auto_load_message(self):
        """Si hay PDF global seleccionado, carga el mensaje del cliente actual automáticamente."""
        if not self._global_pdf_path:
            return
        try:
            trabajador = self.workflow.get_current_client()
            if not trabajador.cliente:
                return
            mensaje = self.workflow.get_message_for_client(
                trabajador, self._global_pdf_path
            )
            if mensaje.es_valido():
                self.word_preview.setPlainText(mensaje.texto)
            else:
                self.word_preview.setPlainText("")
                self._set_status(
                    f"No se encontró mensaje para '{trabajador.cliente}'.",
                    color="orange"
                )
        except Exception:
            pass  # No interrumpir navegación si falla la búsqueda

    def _open_whatsapp(self):
        try:
            self.workflow.open_whatsapp()
            self._set_status("WhatsApp Web abierto.")
        except Exception as e:
            self._show_error("Error abriendo WhatsApp", e)

    def _send_message(self):
        message_text = self.word_preview.toPlainText().strip()
        if not message_text:
            QMessageBox.warning(self, "Mensaje vacío", "No hay mensaje cargado para este cliente.")
            return

        trabajador = self.workflow.get_current_client()
        confirm = QMessageBox.question(
            self, "Confirmar envío",
            f"Enviar mensaje + PDF a {trabajador.cliente} ({trabajador.numero})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.workflow.send_whatsapp_current_client(message_text)
            self._set_status("Mensaje enviado.")
        except Exception as e:
            self._show_error("Error enviando mensaje", e)

    def _send_range(self):
        if not self._global_pdf_path:
            QMessageBox.warning(
                self, "PDF de mensajes requerido",
                "Selecciona primero el PDF de mensajes antes de enviar en rango."
            )
            return

        try:
            start = int(self.range_from.text().strip()) - 1
            end   = int(self.range_to.text().strip()) - 1
        except ValueError:
            QMessageBox.warning(self, "Rango inválido", "Escribe números en los campos Desde y Hasta.")
            return

        self.btn_send_range.setDisabled(True)
        self._set_status(f"Iniciando envío {start+1}–{end+1}...")

        try:
            ok, fail = self.workflow.send_range(start, end, self._global_pdf_path)
            color = "green" if fail == 0 else "orange"
            self._set_status(
                f"Rango completado. Éxitos: {ok} | Fallos: {fail}", color=color
            )
        except Exception as e:
            self._show_error("Error en envío por rango", e)
        finally:
            self.btn_send_range.setDisabled(False)

    # ──────────────────────────────────────────────────────────
    # Auxiliares UI
    # ──────────────────────────────────────────────────────────

    def _fill_form(self, t: Trabajador):
        self.name_line.setText(t.cliente)
        self.number_line.setText(t.numero)
        self.curp_line.setText(t.curp)
        self.rfc_line.setText(t.rfc)
        self.nss_line.setText(t.nss)
        self.email_line.setText(t.correo)
        self.pdf_dir_label.setText(
            f"PDF del cliente: {t.pdf}" if t.pdf else "PDF del cliente: (ninguno)"
        )
        self.folder_label.setText(
            f"Carpeta: {t.carpeta_pdf}" if t.carpeta_pdf else "Carpeta: (ninguna)"
        )
        self.word_preview.setPlainText("")

    def _collect_form(self) -> Trabajador:
        """Lee los campos del formulario y devuelve un Trabajador completo."""
        current = self.workflow.get_current_client()
        return Trabajador(
            id          = current.id,
            cliente     = self.name_line.text().strip(),
            numero      = self.number_line.text().strip(),
            curp        = self.curp_line.text().strip(),
            rfc         = self.rfc_line.text().strip(),
            nss         = self.nss_line.text().strip(),
            correo      = self.email_line.text().strip(),
            carpeta_pdf = current.carpeta_pdf,
            pdf         = current.pdf,
            mensaje     = current.mensaje,
        )

    def _set_status(self, text: str, color: str = "green"):
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(text)

    def _show_error(self, title: str, exc: Exception):
        traceback.print_exc()
        self._set_status(str(exc), color="red")
        QMessageBox.warning(self, title, str(exc))


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Interfaz()
    window.show()
    sys.exit(app.exec_())
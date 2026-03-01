# interfaz.py
import os
import sys

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QGroupBox,
    QFileDialog, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from config import DATA_DIR
from workflow.imss_ti import IMSSTiWorkflow


class Interfaz(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Asistente IMSS")
        self.setGeometry(150, 80, 1200, 720)


        # ÚNICO cerebro
        self.workflow = IMSSTiWorkflow(DATA_DIR)

        
        main_layout = QHBoxLayout()

        # =========================
        # PANEL 1 - CLIENTE
        # =========================
        self.panel1 = QGroupBox("Cliente")
        p1_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()

        self.btn_open_excel = QPushButton("Abrir Excel")
        self.btn_open_excel.clicked.connect(self.load_excel)
        btn_layout.addWidget(self.btn_open_excel)

        self.btn_open_pdf = QPushButton("Abrir PDF")
        self.btn_open_pdf.clicked.connect(self.open_pdf)
        btn_layout.addWidget(self.btn_open_pdf)

        p1_layout.addLayout(btn_layout)

        self.name_line = QLineEdit()
        self.name_line.setPlaceholderText("Nombre del cliente")

        self.number_line = QLineEdit()
        self.number_line.setPlaceholderText("Numero de teléfono")

        self.curp_line = QLineEdit()
        self.curp_line.setPlaceholderText("CURP")

        self.rfc_line = QLineEdit()
        self.rfc_line.setPlaceholderText("RFC")

        self.nss_line = QLineEdit()
        self.nss_line.setPlaceholderText("NSS")

        self.email_line = QLineEdit()
        self.email_line.setPlaceholderText("Email")

        for w in [
            self.name_line, self.number_line, self.curp_line,
            self.rfc_line, self.nss_line, self.email_line
        ]:
            p1_layout.addWidget(w)

        self.pdf_dir_label = QLabel("Dirección de PDF: (ninguna)")
        self.pdf_dir_label.setWordWrap(True)
        p1_layout.addWidget(self.pdf_dir_label)

        save_layout = QHBoxLayout()

        self.btn_save = QPushButton("Guardar cambios")
        self.btn_save.clicked.connect(self.save_changes)
        save_layout.addWidget(self.btn_save)

        self.btn_new = QPushButton("Nuevo cliente")
        self.btn_new.clicked.connect(self.new_client)
        save_layout.addWidget(self.btn_new)

        p1_layout.addLayout(save_layout)

        nav_layout = QHBoxLayout()

        self.btn_prev = QPushButton("Cliente anterior")
        self.btn_prev.clicked.connect(self.prev_row)
        nav_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Siguiente cliente")
        self.btn_next.clicked.connect(self.next_row)
        nav_layout.addWidget(self.btn_next)

        self.btn_goto = QPushButton("Ir al cliente X")
        self.btn_goto.clicked.connect(self.goto_row)
        nav_layout.addWidget(self.btn_goto)

        p1_layout.addLayout(nav_layout)

        self.panel1.setLayout(p1_layout)
        main_layout.addWidget(self.panel1, 3)

        # =========================
        # PANEL 2 - REGISTRO IMSS
        # =========================
        self.panel2 = QGroupBox("Registro")
        p2_layout = QVBoxLayout()

        self.btn_select_folder = QPushButton("Seleccionar carpeta final")
        self.btn_select_folder.clicked.connect(self.select_download_folder)
        p2_layout.addWidget(self.btn_select_folder)

        self.selected_download_label = QLabel("Carpeta final: (ninguna)")
        self.selected_download_label.setWordWrap(True)
        p2_layout.addWidget(self.selected_download_label)

        self.captcha_label = QLabel("Captcha aquí")
        self.captcha_label.setAlignment(Qt.AlignCenter)
        self.captcha_label.setFixedSize(440, 80)
        self.captcha_label.setStyleSheet("border: 1px solid black;")
        p2_layout.addWidget(self.captcha_label)

        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText("Escribe el captcha")
        p2_layout.addWidget(self.captcha_input)

        btn_reg_layout = QHBoxLayout()

        self.btn_register = QPushButton("Registrar cliente")
        self.btn_register.clicked.connect(self.register_client)
        btn_reg_layout.addWidget(self.btn_register)

        self.btn_download = QPushButton("Descargar PDF")
        self.btn_download.clicked.connect(self.download_pdf)
        btn_reg_layout.addWidget(self.btn_download)

        p2_layout.addLayout(btn_reg_layout)

        more_layout = QHBoxLayout()

        self.btn_open_page = QPushButton("Abrir página")
        self.btn_open_page.clicked.connect(self.open_page)
        more_layout.addWidget(self.btn_open_page)

        self.btn_show_captcha = QPushButton("Mostrar captcha")
        self.btn_show_captcha.clicked.connect(self.show_captcha)
        more_layout.addWidget(self.btn_show_captcha)

        p2_layout.addLayout(more_layout)

        self.panel2.setLayout(p2_layout)
        main_layout.addWidget(self.panel2, 2)

        # =========================
        # PANEL 3 - MENSAJE
        # =========================
        self.panel3 = QGroupBox("Mensaje")
        p3_layout = QVBoxLayout()

        self.btn_select_global_pdf = QPushButton("Seleccionar PDF global")
        self.btn_select_global_pdf.clicked.connect(self.select_global_pdf)
        p3_layout.addWidget(self.btn_select_global_pdf)

        self.global_pdf_label = QLabel("PDF global: (ninguno)")
        self.global_pdf_label.setWordWrap(True)
        p3_layout.addWidget(self.global_pdf_label)

        self.word_preview = QTextEdit()
        self.word_preview.setPlaceholderText("Aquí va el mensaje.")
        p3_layout.addWidget(self.word_preview)

        self.btn_send = QPushButton("Enviar mensaje")
        self.btn_send.clicked.connect(self.send_message)
        p3_layout.addWidget(self.btn_send)

        self.btn_open_whatsapp = QPushButton("Abrir WhatsApp Web")
        self.btn_open_whatsapp.clicked.connect(self.open_whatsapp)
        p3_layout.addWidget(self.btn_open_whatsapp)

        range_layout = QHBoxLayout()

        self.range_from = QLineEdit()
        self.range_from.setPlaceholderText("Desde")

        self.range_to = QLineEdit()
        self.range_to.setPlaceholderText("Hasta")

        range_layout.addWidget(self.range_from)
        range_layout.addWidget(self.range_to)

        p3_layout.addLayout(range_layout)

        self.btn_send_range = QPushButton("Enviar mensajes en rango")
        self.btn_send_range.clicked.connect(self.send_range)
        p3_layout.addWidget(self.btn_send_range)

        self.panel3.setLayout(p3_layout)
        main_layout.addWidget(self.panel3, 3)

        # =========================
        # ESTADO
        # =========================
        outer_layout = QVBoxLayout()
        outer_layout.addLayout(main_layout)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: green;")
        outer_layout.addWidget(self.status_label)

        self.setLayout(outer_layout)

    # ======================================================
    # MÉTODOS UI → WORKFLOW
    # ======================================================

    def load_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Excel", "", "Excel (*.xlsx)")
        if not path:
            return

        client = self.workflow.load_excel(path)
        self._fill_form(client)
        self.status_label.setText("Excel cargado")

    def save_changes(self):
        self.workflow.save_current_client(self._collect_data())
        self.status_label.setText("Cambios guardados")

    def new_client(self):
        client = self.workflow.create_new_client(self._collect_data())
        self._fill_form(client)
        self.status_label.setText("Nuevo cliente creado")

    def prev_row(self):
        client = self.workflow.go_previous()
        self._fill_form(client)

    def next_row(self):
        client = self.workflow.go_next()
        self._fill_form(client)

    def goto_row(self):
        index, ok = QInputDialog.getInt(self, "Ir a cliente", "Índice:")
        if ok:
            client = self.workflow.go_to(index)
            self._fill_form(client)

    def open_pdf(self):
        path = self.workflow.open_client_pdf()
        if path and os.path.exists(path):
            os.startfile(path)

    def select_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            self.workflow.download_folder = folder
            self.selected_download_label.setText(f"Carpeta final: {folder}")

    def open_page(self):
        self.workflow.open_imss_page()
        self.status_label.setText("Página abierta")

    def show_captcha(self):
        data = self.workflow.get_captcha()
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.captcha_label.setPixmap(pixmap)

    def register_client(self):
        try:
            pdf = self.workflow.register_current_client(self.captcha_input.text())
            self.pdf_dir_label.setText(f"Dirección de PDF: {pdf}")
            self.status_label.setText("Cliente registrado")
        except Exception as e:
            self.status_label.setText(str(e))

    def download_pdf(self):
        try:
            pdf = self.workflow.download_pdf_current_client(self.captcha_input.text())
            self.pdf_dir_label.setText(f"Dirección de PDF: {pdf}")
            self.status_label.setText("PDF descargado")
        except Exception as e:
            self.status_label.setText(str(e))

    def open_whatsapp(self):
        self.workflow.open_whatsapp()
        self.status_label.setText("WhatsApp abierto")

    def send_message(self):
        try:
            self.workflow.send_whatsapp_current_client(self.word_preview.toPlainText())
            self.status_label.setText("Mensaje enviado")
        except Exception as e:
            self.status_label.setText(str(e))

    def send_range(self):
        try:
            start = int(self.range_from.text())
            end = int(self.range_to.text())
            self.workflow.send_range(start, end, self.word_preview.toPlainText())
            self.status_label.setText("Mensajes enviados")
        except Exception as e:
            self.status_label.setText(str(e))

    def select_global_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF", "", "PDF (*.pdf)")
        if path:
            self.workflow.global_pdf_path = path
            self.global_pdf_label.setText(f"PDF global: {path}")

    # ======================================================
    # AUXILIARES UI
    # ======================================================

    def _fill_form(self, client: dict):
        self.name_line.setText(client.get("Nombre", ""))
        self.number_line.setText(client.get("Numero", ""))
        self.curp_line.setText(client.get("CURP", ""))
        self.rfc_line.setText(client.get("RFC", ""))
        self.nss_line.setText(client.get("NSS", ""))
        self.email_line.setText(client.get("Email", ""))
        self.pdf_dir_label.setText(
            f"Dirección de PDF: {client.get('RutaPDF', '(ninguna)')}"
        )

    def _collect_data(self) -> dict:
        return {
            "Nombre": self.name_line.text(),
            "Numero": self.number_line.text(),
            "CURP": self.curp_line.text(),
            "RFC": self.rfc_line.text(),
            "NSS": self.nss_line.text(),
            "Email": self.email_line.text(),
        }
    
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = Interfaz()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        RuntimeError(type(e), e, e.__traceback__)
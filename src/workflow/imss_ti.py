# workflow/imss_ti.py

import os
from typing import Optional

from tools.excel import ExcelTools
from services.imss_ti import IMSSTiService
from services.whatsapp_web import WhatsAppService
from tools.browser import BrowserTools


class IMSSTiWorkflow:

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        # Estado Excel
        self.excel: Optional[ExcelTools] = None
        self.current_index: int = 0

        # Configuración
        self.download_folder: Optional[str] = None
        self.global_pdf_path: Optional[str] = None
    
        self.imss = IMSSTiService()

        self.whatsapp = WhatsAppService()

    # =========================
    # EXCEL
    # =========================

    def load_excel(self, path: str):
        self.excel = ExcelTools(path)
        self.excel.load()
        self.current_index = 0
        return self.get_current_client()

    def get_current_client(self) -> dict:
        self._ensure_excel()
        return self.excel.get_row(self.current_index)

    def save_current_client(self, data: dict):
        self._ensure_excel()
        self.excel.update_row(self.current_index, data)
        self.excel.save()

    def create_new_client(self, data: dict):
        self._ensure_excel()
        self.excel.append_row(data)
        self.current_index = self.excel.row_count() - 1
        self.excel.save()
        return self.get_current_client()

    def go_next(self):
        self._ensure_excel()
        if self.current_index < self.excel.row_count() - 1:
            self.current_index += 1
        return self.get_current_client()

    def go_previous(self):
        self._ensure_excel()
        if self.current_index > 0:
            self.current_index -= 1
        return self.get_current_client()

    def go_to(self, index: int):
        self._ensure_excel()
        if 0 <= index < self.excel.row_count():
            self.current_index = index
        return self.get_current_client()

    def open_client_pdf(self):
        self._ensure_excel()
        client = self.get_current_client()
        return client.get("RutaPDF")

    # =========================
    # IMSS
    # =========================

    def open_imss_page(self):
        self.imss.start()
        self.imss.open_page()

    def get_captcha(self) -> bytes:
        return self.imss.get_captcha_image()

    def register_current_client(self, captcha_value: str):
        self._ensure_excel()
        self._ensure_download_folder()

        client = self.get_current_client()

        fields = self._map_client_to_imss_fields(client, captcha_value)

        pdf_path = self.imss.register_and_download(
            fields=fields,
            download_folder=self.download_folder
        )

        self.excel.update_row(
            self.current_index,
            {"RutaPDF": pdf_path}
        )

        self.excel.save()

        return pdf_path

    def download_pdf_current_client(self, captcha_value: str):
        self._ensure_excel()
        self._ensure_download_folder()

        client = self.get_current_client()

        fields = self._map_client_to_imss_fields(client, captcha_value)

        pdf_path = self.imss.download_pdf_only(
            fields=fields,
            download_folder=self.download_folder
        )

        self.excel.update_row(
            self.current_index,
            {"RutaPDF": pdf_path}
        )

        self.excel.save()

        return pdf_path

    # =========================
    # WHATSAPP
    # =========================

    def open_whatsapp(self):
        try: 
            self.whatsapp.start_session()
        except Exception:
            pass

    def send_whatsapp_current_client(self, message_text: str):
        self._ensure_excel()

        client = self.get_current_client()

        phone = client.get("Numero")
        pdf_path = client.get("RutaPDF") or self.global_pdf_path

        self.whatsapp.open_chat(phone)
        self.whatsapp.send_message(message_text)

        if pdf_path:
            self.whatsapp.send_pdf(pdf_path)

    def send_range(self, start: int, end: int, message_text: str):
        self._ensure_excel()

        total = self.excel.row_count()

        if start < 0 or end >= total or start > end:
            raise ValueError("Rango inválido")

        for i in range(start, end + 1):
            self.current_index = i
            self.send_whatsapp_current_client(message_text)

    # =========================
    # INTERNOS
    # =========================

    def _ensure_excel(self):
        if not self.excel:
            raise RuntimeError("No hay Excel cargado")

    def _ensure_download_folder(self):
        if not self.download_folder:
            raise RuntimeError("No hay carpeta de descargas seleccionada")

    def _map_client_to_imss_fields(self, client: dict, captcha: str) -> dict:
        return {
            "curp": client.get("CURP", ""),
            "rfc": client.get("RFC", ""),
            "nss": client.get("NSS", ""),
            "email": client.get("Email", ""),
            "emailConfirmacion": client.get("Email", ""),
            "captcha": captcha
        }
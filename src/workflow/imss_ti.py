# workflow/imss_ti.py
from __future__ import annotations
import os

from pathlib import Path
from typing import Optional

from models.trabajador import Trabajador
from models.mensaje import Mensaje
from services.imss_ti import IMSSTiService
from services.whatsapp_web import WhatsAppService
from tools.excel import ExcelTools
from tools.pdf import find_message_for_client


class IMSSTiWorkflow:

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.excel: Optional[ExcelTools] = None
        self.current_index: int = 0
        self.imss = IMSSTiService()

        # Perfil dedicado para WhatsApp — mantiene la sesión entre ejecuciones
        wa_profile_dir = os.path.join(data_dir, "chrome_wa_profile")
        os.makedirs(wa_profile_dir, exist_ok=True)

        from tools.browser import BrowserTools
        wa_browser = BrowserTools(
            user_data_dir=wa_profile_dir,
            profile_directory="Default",
        )
        self.whatsapp = WhatsAppService(browser=wa_browser)


    # ─────────────────────────────────────────
    # Excel / navegación
    # ─────────────────────────────────────────

    def load_excel(self, path: str) -> Trabajador:
        self.excel = ExcelTools(path)
        self.excel.load()
        self.excel.ensure_columns(list(Trabajador.to_row(Trabajador()).keys()))
        self.excel.save()
        self.current_index = 0
        return self.get_current_client()

    def get_current_client(self) -> Trabajador:
        self._ensure_excel()
        return Trabajador.from_row(self.excel.get_row(self.current_index))

    def save_current_client(self, trabajador: Trabajador) -> None:
        self._ensure_excel()
        self.excel.update_row(self.current_index, trabajador.to_row())
        self.excel.save()

    def create_new_client(self) -> Trabajador:
        self._ensure_excel()
        self.excel.add_row(Trabajador().to_row())
        self.current_index = self.excel.row_count() - 1
        self.excel.save()
        return self.get_current_client()

    def go_next(self) -> Trabajador:
        self._ensure_excel()
        if self.current_index < self.excel.row_count() - 1:
            self.current_index += 1
        return self.get_current_client()

    def go_previous(self) -> Trabajador:
        self._ensure_excel()
        if self.current_index > 0:
            self.current_index -= 1
        return self.get_current_client()

    def go_to(self, index: int) -> Trabajador:
        self._ensure_excel()
        if 0 <= index < self.excel.row_count():
            self.current_index = index
        return self.get_current_client()

    def row_count(self) -> int:
        self._ensure_excel()
        return self.excel.row_count()

    def update_field(self, field: str, value: str) -> None:
        """Actualiza un campo puntual del cliente actual y guarda."""
        self._ensure_excel()
        self.excel.update_row(self.current_index, {field: value})
        self.excel.save()

    # ─────────────────────────────────────────
    # Mensaje (PDF global de mensajes)
    # ─────────────────────────────────────────

    def get_message_for_client(
        self, trabajador: Trabajador, pdf_path: str
    ) -> Mensaje:
        from tools.pdf import extract_message
        
        path = Path(pdf_path)
        result = None
        
        # 1. Intentar buscar por ID (si existe en el trabajador)
        if hasattr(trabajador, 'id') and trabajador.id:
            result = extract_message(
                pdf_path=path,
                identifier=str(trabajador.id),
                search_by="id",
                remove_first_line_flag=True,  # Eliminar ID
                normalize_breaks=True
            )
        
        # 2. Si no encontró por ID o no tiene ID, buscar por nombre
        if not result or not result.get("success"):
            result = extract_message(
                pdf_path=path,
                identifier=trabajador.cliente,
                search_by="name",
                remove_first_line_flag=False,  
                normalize_breaks=True
            )
        
        # 3. Devolver resultado
        return Mensaje(
            texto      = result.get("message", ""),      # ⚠️ Cambiado de "text" a "message"
            encontrado = result.get("success", False),   # ⚠️ Cambiado de "found" a "success"
            page_idx   = result.get("page_idx") if result.get("page_idx") is not None else -1,
            pdf_path   = str(path),
        )

    # ─────────────────────────────────────────
    # IMSS
    # ─────────────────────────────────────────

    def open_imss_page(self) -> None:
        self.imss.start()
        self.imss.open_page()

    def get_captcha(self) -> bytes:
        return self.imss.get_captcha_image()

    def register_current_client(self, captcha_value: str) -> str:
        self._ensure_excel()
        trabajador = self.get_current_client()

        if not trabajador.carpeta_pdf:
            raise RuntimeError(
                "El cliente no tiene carpeta de destino (CARPETAPDF). "
                "Selecciónala primero."
            )

        pdf_path = self.imss.register_and_download(
            fields=trabajador.to_imss_fields(captcha_value),
            target_folder=trabajador.carpeta_pdf,
        )

        self.excel.update_row(self.current_index, {"PDF": pdf_path})
        self.excel.save()
        return pdf_path

    def download_pdf_current_client(self, captcha_value: str) -> str:
        self._ensure_excel()
        trabajador = self.get_current_client()

        if not trabajador.carpeta_pdf:
            raise RuntimeError(
                "El cliente no tiene carpeta de destino (CARPETAPDF). "
                "Selecciónala primero."
            )

        pdf_path = self.imss.download_pdf_only(
            fields=trabajador.to_imss_fields(captcha_value),
            target_folder=trabajador.carpeta_pdf,
        )

        self.excel.update_row(self.current_index, {"PDF": pdf_path})
        self.excel.save()
        return pdf_path

    # ─────────────────────────────────────────
    # WhatsApp
    # ─────────────────────────────────────────

    def open_whatsapp(self) -> None:
        try:
            self.whatsapp.start_session()
        except Exception:
            pass

    def send_whatsapp_current_client(self, message_text: str) -> None:
        trabajador = self.get_current_client()

        if not trabajador.numero:
            raise RuntimeError("El cliente no tiene número de teléfono.")
        if not message_text.strip():
            raise RuntimeError("El mensaje está vacío.")
        if not trabajador.pdf:
            raise RuntimeError("El cliente no tiene PDF asignado.")
        if not Path(trabajador.pdf).exists():
            raise RuntimeError(f"El PDF no existe en disco: {trabajador.pdf}")

        self.whatsapp.open_chat(trabajador.numero)
        self.whatsapp.send_message(message_text)
        self.whatsapp.send_pdf(trabajador.pdf)

    def send_range(
        self, start: int, end: int, global_pdf_path: str
    ) -> tuple[int, int]:
        """
        Envía mensajes al rango [start, end] (índices base-0).
        Para cada cliente extrae su mensaje del PDF global.
        Devuelve (éxitos, fallos).
        """
        self._ensure_excel()
        total = self.excel.row_count()

        if start < 0 or end >= total or start > end:
            raise ValueError(f"Rango inválido: [{start}, {end}] (total={total})")

        ok = fail = 0
        for i in range(start, end + 1):
            self.current_index = i
            try:
                trabajador = self.get_current_client()
                mensaje = self.get_message_for_client(trabajador, global_pdf_path)
                if not mensaje.es_valido():
                    raise RuntimeError(
                        f"No se encontró mensaje para '{trabajador.cliente}'."
                    )
                self.send_whatsapp_current_client(mensaje.texto)
                ok += 1
            except Exception as e:
                fail += 1
                print(f"[send_range] Fila {i}: {e}")

        return ok, fail

    # ─────────────────────────────────────────
    # Internos
    # ─────────────────────────────────────────

    def _ensure_excel(self) -> None:
        if not self.excel:
            raise RuntimeError("No hay Excel cargado.")
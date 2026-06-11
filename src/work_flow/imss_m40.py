# work_flow/imss_m40.py
from __future__ import annotations
import os
import logging

from pathlib import Path
from typing import Optional, Tuple

from config import WHATSAPP_CONFIG, VALIDATION, EXCEL_COLUMNS_M40, ERROR_LOG_FILE
from models.trabajador_m40 import TrabajadorM40
from models.mensaje import Mensaje
from services.imss_m40 import IMSSM40Service
from services.whatsapp_web import WhatsAppService
from tools.excel import ExcelTools
from tools.pdf import extract_message
from tools.file import ensure_directory


# Configurar logging
logging.basicConfig(
    filename=ERROR_LOG_FILE,
    level=logging.ERROR,
    format='[%(asctime)s] [%(funcName)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class IMSSM40Workflow:

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.excel: Optional[ExcelTools] = None
        self.current_index: int = 0
        self.imss = IMSSM40Service()

        # Perfil dedicado para WhatsApp - compartido entre TI y M40
        wa_profile_dir = os.path.join(
            data_dir, 
            WHATSAPP_CONFIG["profile_dir_name"]
        )
        os.makedirs(wa_profile_dir, exist_ok=True)

        from tools.browser import BrowserTools
        wa_browser = BrowserTools(
            user_data_dir=wa_profile_dir,
            profile_directory=WHATSAPP_CONFIG["profile_name"],
        )
        self.whatsapp = WhatsAppService(browser=wa_browser)

    def load_excel(self, path: str) -> TrabajadorM40:
        """Carga un archivo Excel."""
        self.excel = ExcelTools(path)
        self.excel.load()
        self.excel.ensure_columns(EXCEL_COLUMNS_M40)
        self.excel.save()
        self.current_index = 0
        return self.get_current_client()

    def get_current_client(self) -> TrabajadorM40:
        """Obtiene el trabajador actual."""
        self._ensure_excel()
        return TrabajadorM40.from_row(self.excel.get_row(self.current_index))

    def save_current_client(self, trabajador: TrabajadorM40) -> None:
        """Guarda el trabajador actual."""
        self._ensure_excel()
        self.excel.update_row(self.current_index, trabajador.to_row())
        self.excel.save()

    def create_new_client(self) -> TrabajadorM40:
        """Crea un nuevo trabajador."""
        self._ensure_excel()
        self.excel.add_row(TrabajadorM40().to_row())
        self.current_index = self.excel.row_count() - 1
        self.excel.save()
        return self.get_current_client()

    def go_next(self) -> TrabajadorM40:
        """Navega al siguiente trabajador."""
        self._ensure_excel()
        if self.current_index < self.excel.row_count() - 1:
            self.current_index += 1
        return self.get_current_client()

    def go_previous(self) -> TrabajadorM40:
        """Navega al trabajador anterior."""
        self._ensure_excel()
        if self.current_index > 0:
            self.current_index -= 1
        return self.get_current_client()

    def go_to(self, index: int) -> TrabajadorM40:
        """Navega a un índice específico."""
        self._ensure_excel()
        if 0 <= index < self.excel.row_count():
            self.current_index = index
        return self.get_current_client()

    def row_count(self) -> int:
        """Retorna el número total de trabajadores."""
        self._ensure_excel()
        return self.excel.row_count()

    def update_field(self, field: str, value: str) -> None:
        """Actualiza un campo del cliente actual."""
        self._ensure_excel()
        self.excel.update_row(self.current_index, {field: value})
        self.excel.save()

    def get_message_for_client(
        self, trabajador: TrabajadorM40, pdf_path: str
    ) -> Mensaje:
        """Extrae el mensaje personalizado para un trabajador."""
        path = Path(pdf_path)
        result = None
        
        if hasattr(trabajador, 'id') and trabajador.id:
            result = extract_message(
                pdf_path=path,
                identifier=str(trabajador.id),
                search_by="id",
                remove_first_line_flag=True,
                normalize_breaks=True
            )
        
        if not result or not result.get("success"):
            result = extract_message(
                pdf_path=path,
                identifier=trabajador.cliente,
                search_by="name",
                remove_first_line_flag=False,  
                normalize_breaks=True
            )
        
        return Mensaje(
            texto      = result.get("message", ""),
            encontrado = result.get("success", False),
            page_idx   = result.get("page_idx") if result.get("page_idx") is not None else -1,
            pdf_path   = str(path),
        )

    def open_imss_page(self) -> None:
        """Abre la página del IMSS M40."""
        self.imss.start()
        self.imss.open_page()

    def get_captcha(self) -> bytes:
        """Obtiene la imagen del captcha."""
        return self.imss.get_captcha_image()

    def register_current_client(self, captcha_value: str) -> Tuple[Optional[str], int]:
        """
        Registra el trabajador actual.
        Retorna (ruta_pdf, intentos). Si la descarga no estaba disponible, ruta_pdf=None
        e intentos refleja el nuevo total acumulado.
        """
        self._ensure_excel()
        trabajador = self.get_current_client()

        if not trabajador.carpeta_pdf:
            raise RuntimeError("No se ha seleccionado una carpeta de destino.")

        if not trabajador.cliente:
            raise RuntimeError("El cliente no tiene nombre. Agrégalo antes de registrar.")

        try:
            carpeta_cliente = self._create_client_folder(
                trabajador.carpeta_pdf,
                trabajador.cliente
            )

            pdf_path = self.imss.register_and_download(
                fields=trabajador.to_imss_fields(captcha_value),
                target_folder=carpeta_cliente,
            )

            if pdf_path is None:
                intentos = self._increment_intentos()
                return None, intentos

            self.excel.update_row(self.current_index, {"PDF": pdf_path})
            self.excel.save()
            return pdf_path, trabajador.intentos
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error registrando cliente: {e}", exc_info=True)
            raise RuntimeError("Error al registrar el cliente.")

    def download_pdf_current_client(self, captcha_value: str) -> Tuple[Optional[str], int]:
        """
        Descarga el PDF del trabajador actual.
        Retorna (ruta_pdf, intentos). Si la descarga no estaba disponible, ruta_pdf=None
        e intentos refleja el nuevo total acumulado.
        """
        self._ensure_excel()
        trabajador = self.get_current_client()

        if not trabajador.carpeta_pdf:
            raise RuntimeError("No se ha seleccionado una carpeta de destino.")

        if not trabajador.cliente:
            raise RuntimeError("El cliente no tiene nombre. Agrégalo antes de descargar.")

        try:
            carpeta_cliente = self._create_client_folder(
                trabajador.carpeta_pdf,
                trabajador.cliente
            )

            pdf_path = self.imss.download_pdf_only(
                fields=trabajador.to_imss_fields(captcha_value),
                target_folder=carpeta_cliente,
            )

            if pdf_path is None:
                intentos = self._increment_intentos()
                return None, intentos

            pdf_path = self._rename_pdf(pdf_path, trabajador.cliente)
            intentos = self._increment_intentos()
            self.excel.update_row(self.current_index, {"PDF": pdf_path})
            self.excel.save()
            return pdf_path, intentos
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error descargando PDF: {e}", exc_info=True)
            raise RuntimeError("Error al descargar el PDF.")

    def _increment_intentos(self) -> int:
        """Suma 1 a la columna INTENTOS del cliente actual y guarda el Excel."""
        trabajador = self.get_current_client()
        new_val = trabajador.intentos + 1
        self.excel.update_row(self.current_index, {"INTENTOS": new_val})
        self.excel.save()
        return new_val

    def _rename_pdf(self, pdf_path: str, client_name: str) -> str:
        """Renombra el PDF descargado a '[cliente]_[nombre_original]'."""
        original = Path(pdf_path)
        if not original.exists():
            return pdf_path
        safe_client = "".join(
            c for c in client_name
            if c.isalnum() or c in VALIDATION["allowed_folder_chars"]
        ).strip() or VALIDATION["fallback_folder_name"]
        new_path = original.parent / f"{safe_client}_{original.name}"
        original.replace(new_path)
        return str(new_path)

    def open_whatsapp(self) -> None:
        """Abre WhatsApp Web."""
        try:
            self.whatsapp.start_session()
        except Exception:
            pass

    def send_whatsapp_current_client(self, message_text: str) -> None:
        """Envía mensaje y PDF por WhatsApp."""
        trabajador = self.get_current_client()

        if not trabajador.numero:
            raise RuntimeError("El cliente no tiene número de teléfono.")
        if not message_text.strip():
            raise RuntimeError("El mensaje está vacío.")
        if not trabajador.pdf:
            raise RuntimeError("El cliente no tiene PDF asignado.")
        if not Path(trabajador.pdf).exists():
            raise RuntimeError("El archivo PDF no existe. Descárgalo primero.")

        self.whatsapp.open_chat(trabajador.numero)
        self.whatsapp.send_message(message_text)
        self.whatsapp.send_pdf(trabajador.pdf)

    def send_range(
        self, start: int, end: int, global_pdf_path: str
    ) -> tuple[int, int]:
        """Envía mensajes por WhatsApp a un rango de trabajadores."""
        self._ensure_excel()
        total = self.excel.row_count()

        if start < 0 or end >= total or start > end:
            raise ValueError(f"Rango inválido. Verifica los números ingresados.")

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
                logging.error(f"Error enviando a fila {i}: {e}", exc_info=True)

        return ok, fail

    def _create_client_folder(self, base_folder: str, client_name: str) -> str:
        """Crea una subcarpeta para el cliente."""
        safe_name = "".join(
            c for c in client_name 
            if c.isalnum() or c in VALIDATION["allowed_folder_chars"]
        ).strip()
        
        if not safe_name:
            safe_name = VALIDATION["fallback_folder_name"]
        
        carpeta_cliente = Path(base_folder) / safe_name
        ensure_directory(carpeta_cliente)
        
        return str(carpeta_cliente)

    def _ensure_excel(self) -> None:
        """Verifica que haya un Excel cargado."""
        if not self.excel:
            raise RuntimeError("No hay Excel cargado. Abre un archivo primero.")
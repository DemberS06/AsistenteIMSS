# services/imss_m40.py
from __future__ import annotations

import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, List

from config import (
    IMSS_M40_URL,
    IMSS_M40_SELECTORS,
    IMSS_M40_REQUIRED_FIELDS,
    IMSS_M40_REGISTRATION_SEQUENCE,
    DOWNLOAD_CONFIG,
    TIMEOUTS,
    DELAYS,
    ERROR_LOG_FILE,
)
from tools.browser import BrowserTools
from tools.file import move_file


# Configurar logging
logging.basicConfig(
    filename=ERROR_LOG_FILE,
    level=logging.ERROR,
    format='[%(asctime)s] [%(funcName)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class IMSSM40Service:

    def __init__(
        self,
        base_url: str = IMSS_M40_URL,
        default_timeout: int = None,
        browser: BrowserTools | None = None,
    ):
        if default_timeout is None:
            default_timeout = TIMEOUTS["default"]
        
        self.temp_download_dir = os.path.join(
            tempfile.gettempdir(), 
            "imss_m40_downloads_temp"  # Carpeta diferente para M40
        )
        os.makedirs(self.temp_download_dir, exist_ok=True)
        
        self.browser = browser or BrowserTools(download_dir=self.temp_download_dir)
        self.base_url = base_url
        self.default_timeout = default_timeout

    def start(self) -> None:
        """Inicia el navegador."""
        try:
            if not self.browser.is_active():
                self.browser.start()
        except Exception as e:
            logging.error(f"Error iniciando navegador: {e}", exc_info=True)
            raise RuntimeError("No se pudo iniciar el navegador.")

    def close(self) -> None:
        """Cierra el navegador."""
        try:
            self.browser.close()
        except Exception as e:
            logging.error(f"Error cerrando navegador: {e}", exc_info=True)

    def open_page(self) -> None:
        """Abre la página del IMSS M40."""
        try:
            self.browser.go_to(self.base_url)
            self.browser.wait_for("tag", "body", timeout=self.default_timeout)
        except Exception as e:
            logging.error(f"Error abriendo página IMSS M40: {e}", exc_info=True)
            raise RuntimeError("No se pudo cargar la página del IMSS. Verifica tu conexión a internet.")

    def get_captcha_image(self) -> bytes:
        """Obtiene la imagen del captcha."""
        # TODO: Implementar cuando se conozca el selector del captcha M40
        try:
            # Placeholder - ajustar selector cuando se implemente
            element = self.browser.wait_for(
                "id", 
                "captchaImg",  # TODO: Actualizar con selector real de M40
                state="visible", 
                timeout=self.default_timeout
            )
            if self.browser.get_size(element).get("width", 0) == 0:
                raise RuntimeError("El captcha no se cargó correctamente. Refresca la página.")
            return element.screenshot_as_png
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error obteniendo captcha: {e}", exc_info=True)
            raise RuntimeError("No se pudo cargar el captcha. Refresca la página.")

    def fill_form(self, fields: Dict[str, str]) -> None:
        """Llena los campos del formulario."""
        try:
            for field_id, value in fields.items():
                self.browser.type(value, by="id", value=field_id, clear=True)
        except Exception as e:
            logging.error(f"Error llenando formulario: {e}", exc_info=True)
            raise RuntimeError("Error al llenar el formulario. Verifica los datos.")

    def validate_field_errors(self) -> Dict[str, str]:
        """Valida errores de campos antes de submit."""
        # TODO: Ajustar selectores según formulario M40
        error_ids = [
            "errorCurp",  # TODO: Actualizar con selectores reales de M40
            "errorRfc",
            "errorNss",
            "errorEmail",
        ]
        errors = {}
        for eid in error_ids:
            try:
                if self.browser.exists("id", eid, timeout=TIMEOUTS["element_check"]):
                    text = self.browser.get_text("id", eid).strip()
                    if text:
                        errors[eid] = text
            except Exception:
                pass
        return errors

    def submit_form(self) -> None:
        """Hace clic en continuar."""
        try:
            # TODO: Actualizar con selector real del botón M40
            self.browser.click("id", "continuar")
            time.sleep(DELAYS["after_submit"])
        except Exception as e:
            logging.error(f"Error enviando formulario: {e}", exc_info=True)
            raise RuntimeError("No se pudo enviar el formulario.")

    def validate_form_error(self) -> None:
        """Valida errorForm después de submit."""
        try:
            # TODO: Actualizar con selector real de M40
            if self.browser.exists("id", "errorForm", timeout=TIMEOUTS["element_check"]):
                text = self.browser.get_text("id", "errorForm").strip()
                if text:
                    raise RuntimeError(text)
        except RuntimeError:
            raise
        except Exception:
            pass

    def process_form(self, fields: Dict[str, str]) -> None:
        """Procesa el formulario completo."""
        try:
            # TODO: Ajustar campos requeridos según M40
            required = IMSS_M40_REQUIRED_FIELDS
            for field in required:
                if not fields.get(field, "").strip():
                    field_names = {
                        "curp": "CURP",
                        "nss": "NSS",
                        "email": "correo electrónico",
                        "emailConfirmacion": "confirmación de correo",
                        "captcha": "captcha"
                    }
                    name = field_names.get(field, field)
                    raise RuntimeError(f"El campo {name} es requerido.")

            self.fill_form(fields)
            
            errors = self.validate_field_errors()
            if errors:
                raise RuntimeError(next(iter(errors.values())))
            
            self.submit_form()
            self.validate_form_error()
            
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error procesando formulario: {e}", exc_info=True)
            raise RuntimeError("Error procesando el formulario. Verifica los datos ingresados.")

    def complete_registration(self) -> None:
        """Completa la secuencia de registro."""
        try:
            # TODO: Ajustar secuencia según flujo M40
            sequence = IMSS_M40_REGISTRATION_SEQUENCE
            
            for btn_id in sequence:
                if not self.browser.exists("id", btn_id, timeout=TIMEOUTS["button_sequence"]):
                    logging.error(f"Botón no encontrado en secuencia: {btn_id}")
                    raise RuntimeError("La página del IMSS cambió su estructura. Contacta a soporte.")
                self.browser.click("id", btn_id)
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error completando registro: {e}", exc_info=True)
            raise RuntimeError("Error completando el registro en el IMSS.")

    def register(self, fields: Dict[str, str]) -> None:
        """Registra un trabajador."""
        try:
            self.process_form(fields)
            
            # TODO: Actualizar selector según mensaje M40
            if self.browser.exists("id", "mensajeYaRegistrado", timeout=TIMEOUTS["button_sequence"]):
                raise RuntimeError("El trabajador ya está registrado en el sistema IMSS.")
            
            self.complete_registration()
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error en registro: {e}", exc_info=True)
            raise RuntimeError("Error al registrar el trabajador.")

    def _wait_for_all_downloads(self, timeout: int = None) -> bool:
        """Espera a que terminen todas las descargas."""
        if timeout is None:
            timeout = TIMEOUTS["download"]
        
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                entries = os.listdir(self.temp_download_dir)
                still_downloading = any(
                    name.endswith(DOWNLOAD_CONFIG["crdownload_extension"]) 
                    for name in entries
                )
                if not still_downloading:
                    return True
            except FileNotFoundError:
                pass
            time.sleep(DELAYS["download_poll"])
        return False

    def _get_temp_files(self) -> List[str]:
        """Lista archivos descargados en temp."""
        try:
            entries = os.listdir(self.temp_download_dir)
            return [
                f for f in entries 
                if not f.endswith(DOWNLOAD_CONFIG["crdownload_extension"])
            ]
        except FileNotFoundError:
            return []

    def download_pdfs(
        self,
        click_selector: str = None,
        click_count: int = None,
    ) -> List[str]:
        """Descarga los PDFs del trabajador."""
        # TODO: Ajustar selectores según página M40
        if click_selector is None:
            click_selector = "span.glyphicon.glyphicon-file"  # TODO: Actualizar
        if click_count is None:
            click_count = DOWNLOAD_CONFIG["pdf_click_count"]
        
        try:
            # TODO: Verificar selector de "no registrado" para M40
            if self.browser.exists("id", "submitCancelar", timeout=TIMEOUTS["element_check"]):
                raise RuntimeError("El trabajador no ha sido registrado. Usa 'Registrar cliente' primero.")
            
            icons = self.browser.find_all_css(click_selector)
            if not icons:
                logging.error("No se encontraron iconos de PDF")
                raise RuntimeError("No se encontraron PDFs para descargar. Verifica que el registro se completó.")
            
            for i in range(min(click_count, len(icons))):
                try:
                    icons[i].click()
                    time.sleep(DELAYS["pdf_icon_click"])
                except Exception:
                    try:
                        icons = self.browser.find_all_css(click_selector)
                        if len(icons) > i:
                            icons[i].click()
                            time.sleep(DELAYS["pdf_icon_click"])
                    except Exception:
                        pass
            
            ok = self._wait_for_all_downloads()
            if not ok:
                logging.error("Timeout esperando descargas")
                raise RuntimeError("Las descargas están tardando demasiado. Verifica tu conexión a internet.")
            
            time.sleep(DELAYS["download_complete"])
            
            temp_files = self._get_temp_files()
            if not temp_files:
                logging.error("No se detectaron archivos descargados")
                raise RuntimeError("No se descargó ningún archivo. Intenta de nuevo.")
            
            return [os.path.join(self.temp_download_dir, f) for f in temp_files]
            
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error descargando PDFs: {e}", exc_info=True)
            raise RuntimeError("Error al descargar los PDFs.")

    def register_and_download(
        self,
        fields: Dict[str, str],
        target_folder: str,
    ) -> str:
        """Registra y descarga PDFs."""
        try:
            if not target_folder:
                raise RuntimeError("No se ha seleccionado una carpeta de destino.")
            
            self.register(fields)
            temp_paths = self.download_pdfs()
            
            moved_paths = []
            for temp_path in temp_paths:
                dest = Path(target_folder) / Path(temp_path).name
                move_file(Path(temp_path), dest)
                moved_paths.append(str(dest))
            
            try:
                # TODO: Actualizar selector del botón salir para M40
                self.browser.click("id", "salir")
                time.sleep(DELAYS["browser_exit"])
            except Exception:
                pass
            
            return moved_paths[0] if moved_paths else ""
            
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error en registro y descarga: {e}", exc_info=True)
            raise RuntimeError("Error al registrar y descargar los documentos.")

    def download_pdf_only(
        self,
        fields: Dict[str, str],
        target_folder: str,
    ) -> str:
        """Descarga PDFs sin registrar."""
        try:
            if not target_folder:
                raise RuntimeError("No se ha seleccionado una carpeta de destino.")
            
            self.process_form(fields)
            temp_paths = self.download_pdfs()
            
            moved_paths = []
            for temp_path in temp_paths:
                dest = Path(target_folder) / Path(temp_path).name
                move_file(Path(temp_path), dest)
                moved_paths.append(str(dest))
            
            try:
                # TODO: Actualizar selector del botón salir para M40
                self.browser.click("id", "salir")
                time.sleep(DELAYS["browser_exit"])
            except Exception:
                pass
            
            return moved_paths[0] if moved_paths else ""
            
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error descargando PDF: {e}", exc_info=True)
            raise RuntimeError("Error al descargar el PDF.")
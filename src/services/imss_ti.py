# services/imss_ti.py
from __future__ import annotations

import os
import time
import tempfile
from pathlib import Path
from typing import Dict, List

from config import (
    IMSS_TI_URL,
    IMSS_TI_SELECTORS,
    IMSS_TI_REQUIRED_FIELDS,
    IMSS_TI_REGISTRATION_SEQUENCE,
    DOWNLOAD_CONFIG,
    TIMEOUTS,
    DELAYS,
)
from tools.browser import BrowserTools
from tools.file import move_file


class IMSSTiService:

    def __init__(
        self,
        base_url: str = IMSS_TI_URL,
        default_timeout: int = None,
        browser: BrowserTools | None = None,
    ):
        # Usar timeout de config si no se especifica
        if default_timeout is None:
            default_timeout = TIMEOUTS["default"]
        
        # Usar nombre de carpeta temporal de config
        self.temp_download_dir = os.path.join(
            tempfile.gettempdir(), 
            DOWNLOAD_CONFIG["temp_dir_name"]
        )
        os.makedirs(self.temp_download_dir, exist_ok=True)
        
        self.browser = browser or BrowserTools(download_dir=self.temp_download_dir)
        
        self.base_url = base_url
        self.default_timeout = default_timeout

    def start(self) -> None:
        try:
            if not self.browser.is_active():
                self.browser.start()
        except Exception as e:
            raise RuntimeError(f"[start] {e}")

    def close(self) -> None:
        try:
            self.browser.close()
        except Exception as e:
            raise RuntimeError(f"[close] {e}")

    def open_page(self) -> None:
        try:
            self.browser.go_to(self.base_url)
            self.browser.wait_for("tag", "body", timeout=self.default_timeout)
        except Exception as e:
            raise RuntimeError(f"[open_page] {e}")

    def get_captcha_image(self) -> bytes:
        try:
            element = self.browser.wait_for(
                "id", 
                IMSS_TI_SELECTORS["captcha_img"], 
                state="visible", 
                timeout=self.default_timeout
            )
            if self.browser.get_size(element).get("width", 0) == 0:
                raise RuntimeError("Captcha rendered with zero size.")
            return element.screenshot_as_png
        except Exception as e:
            raise RuntimeError(f"[get_captcha_image] {e}")

    def fill_form(self, fields: Dict[str, str]) -> None:
        try:
            for field_id, value in fields.items():
                self.browser.type(value, by="id", value=field_id, clear=True)
        except Exception as e:
            raise RuntimeError(f"[fill_form] {e}")

    def validate_field_errors(self) -> Dict[str, str]:
        error_ids = [
            IMSS_TI_SELECTORS["error_curp"],
            IMSS_TI_SELECTORS["error_rfc"],
            IMSS_TI_SELECTORS["error_nss"],
            IMSS_TI_SELECTORS["error_email"],
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
        try:
            self.browser.click("id", IMSS_TI_SELECTORS["continuar_button"])
            time.sleep(DELAYS["after_submit"])
        except Exception as e:
            raise RuntimeError(f"[submit_form] {e}")

    def validate_form_error(self) -> None:
        try:
            if self.browser.exists(
                "id", 
                IMSS_TI_SELECTORS["error_form"], 
                timeout=TIMEOUTS["element_check"]
            ):
                text = self.browser.get_text("id", IMSS_TI_SELECTORS["error_form"]).strip()
                if text:
                    raise RuntimeError(text)
        except RuntimeError:
            raise
        except Exception:
            pass

    def process_form(self, fields: Dict[str, str]) -> None:
        try:
            # Usar campos requeridos de config
            required = IMSS_TI_REQUIRED_FIELDS
            for field in required:
                if not fields.get(field, "").strip():
                    raise RuntimeError(f"Campo requerido vacío: '{field}'")

            # Llenar formulario
            self.fill_form(fields)
            
            # Validar errores de campos ANTES de submit
            errors = self.validate_field_errors()
            if errors:
                raise RuntimeError(next(iter(errors.values())))
            
            # Hacer clic en continuar
            self.submit_form()
            
            # Validar errorForm DESPUÉS de submit
            self.validate_form_error()
            
        except Exception as e:
            raise RuntimeError(f"[process_form] {e}")

    def complete_registration(self) -> None:
        try:
            # Usar secuencia de config
            sequence = IMSS_TI_REGISTRATION_SEQUENCE
            
            for btn_id in sequence:
                if not self.browser.exists("id", btn_id, timeout=TIMEOUTS["button_sequence"]):
                    raise RuntimeError(f"Botón esperado no encontrado: '{btn_id}'")
                self.browser.click("id", btn_id)
        except Exception as e:
            raise RuntimeError(f"[complete_registration] {e}")

    def register(self, fields: Dict[str, str]) -> None:
        try:
            self.process_form(fields)
            
            # Verificar si ya está registrado
            if self.browser.exists(
                "id", 
                IMSS_TI_SELECTORS["mensaje_ya_registrado"], 
                timeout=TIMEOUTS["button_sequence"]
            ):
                raise RuntimeError("El trabajador ya está registrado.")
            
            self.complete_registration()
        except Exception as e:
            raise RuntimeError(f"[register] {e}")

    def _wait_for_all_downloads(self, timeout: int = None) -> bool:
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
        # Usar valores de config si no se especifican
        if click_selector is None:
            click_selector = IMSS_TI_SELECTORS["pdf_icons"]
        if click_count is None:
            click_count = DOWNLOAD_CONFIG["pdf_click_count"]
        
        try:
            # Verificar si el trabajador está registrado
            if self.browser.exists(
                "id", 
                IMSS_TI_SELECTORS["submit_cancelar"], 
                timeout=TIMEOUTS["element_check"]
            ):
                raise RuntimeError("El trabajador no ha sido registrado. Usa 'Registrar cliente' primero.")
            
            icons = self.browser.find_all_css(click_selector)
            if not icons:
                raise RuntimeError("No se encontraron iconos de PDF en la página.")
            
            # Hacer clic en los iconos
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
            
            # Esperar descargas
            ok = self._wait_for_all_downloads()
            if not ok:
                raise RuntimeError("Timeout esperando descargas.")
            
            time.sleep(DELAYS["download_complete"])
            
            # Obtener archivos descargados
            temp_files = self._get_temp_files()
            if not temp_files:
                raise RuntimeError("No se detectaron archivos descargados.")
            
            return [os.path.join(self.temp_download_dir, f) for f in temp_files]
            
        except Exception as e:
            raise RuntimeError(f"[download_pdfs] {e}")

    def register_and_download(
        self,
        fields: Dict[str, str],
        target_folder: str,
    ) -> str:
        try:
            if not target_folder:
                raise RuntimeError("No se definió carpeta de destino.")
            
            self.register(fields)
            temp_paths = self.download_pdfs()
            
            moved_paths = []
            for temp_path in temp_paths:
                dest = Path(target_folder) / Path(temp_path).name
                move_file(Path(temp_path), dest)
                moved_paths.append(str(dest))
            
            # Cerrar sesión
            try:
                self.browser.click("id", IMSS_TI_SELECTORS["salir_button"])
                time.sleep(DELAYS["browser_exit"])
            except Exception:
                pass
            
            return moved_paths[0] if moved_paths else ""
            
        except Exception as e:
            raise RuntimeError(f"[register_and_download] {e}")

    def download_pdf_only(
        self,
        fields: Dict[str, str],
        target_folder: str,
    ) -> str:
        try:
            if not target_folder:
                raise RuntimeError("No se definió carpeta de destino.")
            
            self.process_form(fields)
            temp_paths = self.download_pdfs()
            
            moved_paths = []
            for temp_path in temp_paths:
                dest = Path(target_folder) / Path(temp_path).name
                move_file(Path(temp_path), dest)
                moved_paths.append(str(dest))
            
            # Cerrar sesión
            try:
                self.browser.click("id", IMSS_TI_SELECTORS["salir_button"])
                time.sleep(DELAYS["browser_exit"])
            except Exception:
                pass
            
            return moved_paths[0] if moved_paths else ""
            
        except Exception as e:
            raise RuntimeError(f"[download_pdf_only] {e}")
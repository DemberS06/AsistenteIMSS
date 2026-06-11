# services/imss_m40.py
from __future__ import annotations

import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    IMSS_M40_URL,
    IMSS_M40_SELECTORS,
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
            "imss_m40_downloads_temp"
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
        try:
            element = self.browser.wait_for(
                "id", 
                IMSS_M40_SELECTORS["captcha_img"],
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
        error_selectors = {
            "error_curp": IMSS_M40_SELECTORS.get("error_curp"),
            "error_email": IMSS_M40_SELECTORS.get("error_email"),
        }
        
        errors = {}
        for error_name, error_id in error_selectors.items():
            if error_id is None:
                continue
            try:
                if self.browser.exists("id", error_id, timeout=TIMEOUTS["element_check"]):
                    text = self.browser.get_text("id", error_id).strip()
                    if text:
                        errors[error_name] = text
            except Exception:
                pass
        return errors

    def wait_for_loading_modal_to_disappear(self) -> None:
        """
        Espera a que desaparezca el modal de carga 
        "Tu petición se está procesando... Espera un momento."
        """
        try:
            # CSS selector del modal de carga
            loading_modal_selector = "div.blockUI.blockMsg.blockPage"
            
            # Esperar a que aparezca primero (opcional)
            time.sleep(0.5)
            
            # Esperar a que desaparezca
            end_time = time.time() + TIMEOUTS["long"]  # 30 segundos
            while time.time() < end_time:
                try:
                    modals = self.browser.find_all_css(loading_modal_selector)
                    
                    # Si no hay modales, o están ocultos, continuar
                    if not modals:
                        return
                    
                    # Verificar si el modal está visible
                    visible = False
                    for modal in modals:
                        try:
                            if self.browser.is_displayed(modal):
                                visible = True
                                break
                        except Exception:
                            pass
                    
                    if not visible:
                        return
                    
                except Exception:
                    # Si hay error al buscar el modal, asumir que ya no está
                    return
                
                time.sleep(0.3)
            
            # Si llegamos aquí, el timeout se cumplió
            logging.error("Timeout esperando que desaparezca el modal de carga")
            raise RuntimeError("La página está tardando demasiado en procesar. Intenta de nuevo.")
            
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error esperando modal de carga: {e}", exc_info=True)
            # No lanzar error, intentar continuar

    def submit_form(self) -> None:
        """Hace clic en buscar y espera a que termine de procesar."""
        try:
            self.browser.click("id", IMSS_M40_SELECTORS["buscar_button"])
            time.sleep(DELAYS["after_submit"])
            
            # Esperar a que desaparezca el modal de carga
            self.wait_for_loading_modal_to_disappear()
            
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error enviando formulario: {e}", exc_info=True)
            raise RuntimeError("No se pudo enviar el formulario.")

    def validate_form_error(self) -> None:
        """Valida errorForm después de submit."""
        try:
            error_form_id = IMSS_M40_SELECTORS.get("error_form")
            if error_form_id and self.browser.exists("id", error_form_id, timeout=TIMEOUTS["element_check"]):
                text = self.browser.get_text("id", error_form_id).strip()
                if text:
                    raise RuntimeError(text)
        except RuntimeError:
            raise
        except Exception:
            pass

    def process_form(self, fields: Dict[str, str]) -> None:
        """Procesa el formulario completo (primera pantalla)."""
        try:
            # Validar que todos los campos requeridos tengan valor
            required_ids = [
                IMSS_M40_SELECTORS["curp_input"],
                IMSS_M40_SELECTORS["email_input"],
                IMSS_M40_SELECTORS["email_confirm_input"],
                IMSS_M40_SELECTORS["captcha_input"],
            ]
            
            field_names = {
                IMSS_M40_SELECTORS["curp_input"]: "CURP",
                IMSS_M40_SELECTORS["email_input"]: "correo electrónico",
                IMSS_M40_SELECTORS["email_confirm_input"]: "confirmación de correo",
                IMSS_M40_SELECTORS["captcha_input"]: "captcha",
            }
            
            for field_id in required_ids:
                if not fields.get(field_id, "").strip():
                    name = field_names.get(field_id, field_id)
                    raise RuntimeError(f"El campo {name} es requerido.")

            self.fill_form(fields)
            
            errors = self.validate_field_errors()
            if errors:
                raise RuntimeError(next(iter(errors.values())))
            
            self.submit_form()  # Ahora incluye espera del modal
            self.validate_form_error()
            
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error procesando formulario: {e}", exc_info=True)
            raise RuntimeError("Error procesando el formulario. Verifica los datos ingresados.")

    def complete_registration(self) -> None:
        """Completa la secuencia de registro M40."""
        try:
            sequence = IMSS_M40_REGISTRATION_SEQUENCE
            
            for step_id in sequence:
                # Paso 1: Abrir tile de inscripción
                if step_id == "tile_inscripcion":
                    if not self.browser.exists("id", IMSS_M40_SELECTORS["tile_inscripcion"], timeout=TIMEOUTS["button_sequence"]):
                        logging.error(f"Tile inscripción no encontrado: {step_id}")
                        raise RuntimeError("No se encontró el menú de inscripción. La página cambió su estructura.")
                    self.browser.click("id", IMSS_M40_SELECTORS["tile_inscripcion"])
                    time.sleep(DELAYS["after_click"])
                
                # Paso 2: Descargar PDF (se maneja en download_pdfs)
                # Aquí solo esperamos que esté disponible
                
                # Paso 3: Cerrar wizard
                elif step_id == "cerrar_wizard_button":
                    if not self.browser.exists("id", IMSS_M40_SELECTORS["cerrar_wizard_button"], timeout=TIMEOUTS["button_sequence"]):
                        logging.error(f"Botón cerrar wizard no encontrado: {step_id}")
                        raise RuntimeError("No se encontró el botón de cerrar. La página cambió su estructura.")
                    self.browser.click("id", IMSS_M40_SELECTORS["cerrar_wizard_button"])
                    time.sleep(DELAYS["after_click"])
                
                # Paso 4: Aceptar (botón sin ID, buscar por texto)
                elif step_id == "aceptar_button_text":
                    try:
                        # Buscar botón por texto "Aceptar"
                        aceptar_buttons = self.browser.find_all_xpath(
                            f"//button[contains(., '{IMSS_M40_SELECTORS['aceptar_button_text']}')]"
                        )
                        if not aceptar_buttons:
                            logging.error("Botón Aceptar no encontrado")
                            raise RuntimeError("No se encontró el botón Aceptar. La página cambió su estructura.")
                        aceptar_buttons[0].click()
                        time.sleep(DELAYS["after_click"])
                    except Exception as e:
                        logging.error(f"Error al hacer clic en Aceptar: {e}", exc_info=True)
                        raise RuntimeError("No se pudo confirmar la acción. Intenta de nuevo.")
                
        except RuntimeError:
            raise
        except Exception as e:
            logging.error(f"Error completando registro: {e}", exc_info=True)
            raise RuntimeError("Error completando el registro en el IMSS.")

    def register(self, fields: Dict[str, str]) -> None:
        """Registra un trabajador en M40."""
        try:
            self.process_form(fields)
            
            # Verificar si ya está registrado
            mensaje_registrado_id = IMSS_M40_SELECTORS.get("mensaje_ya_registrado")
            if mensaje_registrado_id and self.browser.exists("id", mensaje_registrado_id, timeout=TIMEOUTS["button_sequence"]):
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

        # Fase 1: esperar a que aparezca al menos un archivo (la descarga inició)
        while time.time() < end_time:
            try:
                if os.listdir(self.temp_download_dir):
                    break
            except FileNotFoundError:
                pass
            time.sleep(DELAYS["download_poll"])
        else:
            return False  # nunca inició la descarga

        # Fase 2: esperar a que desaparezcan los .crdownload (la descarga terminó)
        while time.time() < end_time:
            try:
                entries = os.listdir(self.temp_download_dir)
                if not any(f.endswith(DOWNLOAD_CONFIG["crdownload_extension"]) for f in entries):
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

    def _switch_to_pagos_frame(self, timeout: int = None) -> bool:
        """Busca el iframe que contiene #pagos y cambia el contexto a él."""
        if timeout is None:
            timeout = TIMEOUTS["default"]

        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                iframes = self.browser.find_all_css("iframe")
                for iframe in iframes:
                    try:
                        self.browser.switch_to_frame(element=iframe)
                        if self.browser.find_all_css("#pagos"):
                            return True
                        self.browser.switch_to_default()
                    except Exception:
                        try:
                            self.browser.switch_to_default()
                        except Exception:
                            pass
            except Exception:
                pass
            time.sleep(0.5)

        return False

    def is_download_available(self) -> bool:
        """Verifica si el link de descarga PDF está presente y visible."""
        try:
            element = self.browser.run_js(
                "return document.querySelector('[onclick*=\"imprimePago\"]');"
            )
            return element is not None and self.browser.is_displayed(element)
        except Exception:
            return False

    def download_pdfs(self) -> List[str]:
        """
        Descarga los PDFs del trabajador M40.
        Debe llamarse DESPUÉS de abrir el tile de inscripción.
        El PDF se descarga haciendo clic en <a class="link print"> que ejecuta imprimePago(...)
        """
        try:
            clicked = self.browser.run_js("""
                var links = document.querySelectorAll('[onclick*="imprimePago"]');
                for (var i = 0; i < links.length; i++) {
                    if (links[i].offsetParent !== null) {
                        links[i].scrollIntoView({block: 'center'});
                        links[i].click();
                        return true;
                    }
                }
                return false;
            """)

            if not clicked:
                logging.error("No se encontró link de descarga via JS querySelector")
                raise RuntimeError("No se encontraron PDFs para descargar. Verifica que el registro se completó.")
            
            ok = self._wait_for_all_downloads()
            if not ok:
                logging.error("Timeout esperando descargas")
                raise RuntimeError("Las descargas están tardando demasiado. Verifica tu conexión a internet.")
            
            time.sleep(DELAYS["download_complete"])
            
            temp_files = self._get_temp_files()
            if not temp_files:
                logging.error("No se detectaron archivos descargados")
                raise RuntimeError("No se descargó ningún archivo. Intenta de nuevo.")
            
            logging.info(f"Archivos descargados: {temp_files}")
            
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
    ) -> Optional[str]:
        """
        Registra y descarga PDFs.
        Retorna la ruta del PDF descargado, o None si la descarga no está disponible.
        """
        try:
            if not target_folder:
                raise RuntimeError("No se ha seleccionado una carpeta de destino.")

            # Paso 1: Llenar formulario y hacer clic en Buscar (incluye espera del modal)
            self.process_form(fields)

            # Paso 2: Abrir tile de inscripción
            if not self.browser.exists("id", IMSS_M40_SELECTORS["tile_inscripcion"], timeout=TIMEOUTS["button_sequence"]):
                raise RuntimeError("No se encontró el menú de inscripción.")
            self.browser.click("id", IMSS_M40_SELECTORS["tile_inscripcion"])

            # Cambiar al iframe que contiene #pagos
            if not self._switch_to_pagos_frame():
                logging.info("Tabla de pagos no encontrada en ningún iframe.")
                self.open_page()
                return None

            # Paso 3: Verificar si la descarga está disponible (dentro del iframe)
            if not self.is_download_available():
                logging.info("Descarga no disponible para este trabajador.")
                self.browser.switch_to_default()
                self.open_page()
                return None

            # Paso 4: Descargar PDF (dentro del iframe)
            temp_paths = self.download_pdfs()

            # Volver al documento principal antes de continuar
            self.browser.switch_to_default()

            # Paso 5: Cerrar wizard
            try:
                if self.browser.exists("id", IMSS_M40_SELECTORS["cerrar_wizard_button"], timeout=TIMEOUTS["button_sequence"]):
                    self.browser.click("id", IMSS_M40_SELECTORS["cerrar_wizard_button"])
                    time.sleep(DELAYS["after_click"])
            except Exception:
                pass

            # Paso 6: Aceptar
            try:
                aceptar_buttons = self.browser.find_all_xpath(
                    f"//button[contains(., '{IMSS_M40_SELECTORS['aceptar_button_text']}')]"
                )
                if aceptar_buttons:
                    aceptar_buttons[0].click()
                    time.sleep(DELAYS["after_click"])
            except Exception:
                pass  # No crítico si no encuentra el botón Aceptar

            # Mover archivos a carpeta destino
            moved_paths = []
            for temp_path in temp_paths:
                dest = Path(target_folder) / Path(temp_path).name
                move_file(Path(temp_path), dest)
                moved_paths.append(str(dest))

            # Regresar a página principal tras descarga exitosa
            try:
                self.open_page()
            except Exception as e:
                logging.error(f"No se pudo regresar a página principal: {e}", exc_info=True)
                self.close()

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
        """Descarga PDFs sin registrar (trabajador ya registrado)."""
        # Para M40, el flujo es el mismo que register_and_download
        # porque no hay un "modo descarga" separado
        return self.register_and_download(fields, target_folder)
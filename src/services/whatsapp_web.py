# services/whatsapp_web.py
from __future__ import annotations

import os
import time
import logging
from typing import Optional

from config import WHATSAPP_URL, WHATSAPP_SELECTORS, TIMEOUTS, DELAYS, ERROR_LOG_FILE
from tools.browser import BrowserTools


# Configurar logging
logging.basicConfig(
    filename=ERROR_LOG_FILE,
    level=logging.ERROR,
    format='[%(asctime)s] [%(funcName)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class WhatsAppService:

    def __init__(
        self,
        browser: BrowserTools | None = None,
        default_timeout: int = None,
    ):
        if default_timeout is None:
            default_timeout = TIMEOUTS["default"]
        
        self.browser = browser or BrowserTools()
        self.default_timeout = default_timeout
        self._chat_open = False

    def start_session(self) -> None:
        """Inicia sesión de WhatsApp Web."""
        if not self.browser.is_active():
            self.browser.start()
        self.browser.go_to(WHATSAPP_URL)
        self.browser.wait_for("tag", "body", timeout=TIMEOUTS["whatsapp_login"])

    def close_session(self) -> None:
        """Cierra la sesión del navegador."""
        self.browser.close()
        self._chat_open = False

    def is_logged_in(self) -> bool:
        """Verifica si el usuario está logueado."""
        try:
            driver = self.browser.driver
            if driver is None:
                return False

            url_ok = "web.whatsapp.com" in (driver.current_url or "")
            
            cookies_ok = False
            try:
                ck = driver.get_cookies() or []
                for c in ck:
                    dn = (c.get("domain") or "").lower()
                    nm = (c.get("name")   or "").lower()
                    if "whatsapp" in dn or "whatsapp" in nm:
                        cookies_ok = True
                        break
                if not cookies_ok and len(ck) >= 2:
                    cookies_ok = True
            except Exception:
                cookies_ok = False

            dom_ok = False
            try:
                dom_checks = (
                    WHATSAPP_SELECTORS["search_inputs"] + 
                    WHATSAPP_SELECTORS["conversation_panel"]
                )
                for sel in dom_checks:
                    if self.browser.find_all_css(sel):
                        dom_ok = True
                        break
            except Exception:
                dom_ok = False

            return url_ok or cookies_ok or dom_ok

        except Exception:
            return False

    def open_chat(self, phone_number: str) -> None:
        """Abre el chat de un contacto."""
        if not self.is_logged_in():
            raise RuntimeError("WhatsApp Web no está abierto. Ábrelo primero.")

        phone = str(phone_number).strip().lstrip("+")

        opened = self._open_chat_by_search(phone)
        if not opened:
            opened = self._open_chat_by_url(phone)

        if not opened:
            logging.error(f"No se pudo abrir chat con {phone_number}")
            raise RuntimeError(
                f"No se pudo abrir el chat con {phone_number}. "
                "Verifica que el número esté guardado en tus contactos."
            )

        self._chat_open = True

    def _conversation_is_open(self, search_field=None) -> bool:
        """Verifica si hay una conversación abierta."""
        try:
            for sel in WHATSAPP_SELECTORS["conversation_panel"]:
                if self.browser.find_all_css(sel):
                    return True

            all_inputs = self.browser.find_all_css("div[contenteditable='true']")
            for el in all_inputs:
                try:
                    if search_field is not None and self.browser.same_element(el, search_field):
                        continue
                    size = self.browser.get_size(el)
                    if size.get("height", 0) > 10 and size.get("width", 0) > 10:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _find_chat_input(self):
        """Encuentra el campo de entrada del chat."""
        for sel in WHATSAPP_SELECTORS["chat_input"]:
            try:
                boxes = self.browser.find_all_css(sel)
                for b in boxes:
                    if self.browser.is_displayed(b) and self.browser.get_size(b).get("height", 0) > 8:
                        return b
            except Exception:
                continue

        try:
            all_inputs = self.browser.find_all_css("div[contenteditable='true']")
            max_area, candidate = 0, None
            for el in all_inputs:
                try:
                    if not self.browser.is_displayed(el):
                        continue
                    s = self.browser.get_size(el)
                    area = s.get("height", 0) * s.get("width", 0)
                    if area > max_area and s.get("height", 0) > 8:
                        candidate, max_area = el, area
                except Exception:
                    continue
            return candidate
        except Exception:
            return None

    def _open_chat_by_search(self, phone: str) -> bool:
        """Intenta abrir chat usando la búsqueda."""
        search_field = None
        end = time.time() + TIMEOUTS["search_field"]
        
        while time.time() < end and search_field is None:
            search_field = self.browser.find_first(WHATSAPP_SELECTORS["search_inputs"])
            if search_field is None:
                time.sleep(DELAYS["whatsapp_doc_click"])

        if search_field is None:
            return False

        try:
            self.browser.focus_and_scroll(search_field)
            try:
                search_field.click()
            except Exception:
                self.browser.run_js("arguments[0].click();", search_field)

            self.browser.clear_and_type(search_field, phone)
            time.sleep(DELAYS["whatsapp_search"])

            self.browser.send_keys_to(search_field, "\n")

            end2 = time.time() + TIMEOUTS["search_results"]
            while time.time() < end2:
                if self._conversation_is_open(search_field):
                    return True
                time.sleep(DELAYS["whatsapp_doc_click"])

            for result_sel in ("div[role='option']", "div[role='button'][data-testid]"):
                try:
                    els = self.browser.find_all_css(result_sel)
                    if els:
                        els[0].click()
                        time.sleep(DELAYS["whatsapp_search"])
                        if self._conversation_is_open(search_field):
                            return True
                except Exception:
                    pass

        except Exception:
            pass

        return False

    def _open_chat_by_url(self, phone: str) -> bool:
        """Intenta abrir chat por URL."""
        try:
            self.browser.go_to(f"{WHATSAPP_URL}send?phone={phone}")
            self.browser.wait_until(
                lambda d: self.is_logged_in(), 
                timeout=TIMEOUTS["whatsapp_url"]
            )
            time.sleep(DELAYS["whatsapp_clip"])
            
            end = time.time() + TIMEOUTS["whatsapp_chat_open"]
            while time.time() < end:
                if self._conversation_is_open():
                    return True
                time.sleep(0.4)
        except Exception:
            pass
        return False

    def send_message(self, message: str) -> None:
        """Envía un mensaje de texto."""
        if not self._chat_open:
            raise RuntimeError("No hay ningún chat abierto.")

        input_box = self._find_chat_input()
        if input_box is None:
            logging.error("No se encontró el campo de texto del chat")
            raise RuntimeError("No se encontró el campo de texto del chat. Verifica que WhatsApp esté cargado.")

        try:
            input_box.click()
        except Exception:
            try:
                self.browser.focus(input_box)
            except Exception:
                pass

        lines = str(message).splitlines()
        for i, line in enumerate(lines):
            input_box.send_keys(line)
            if i < len(lines) - 1:
                input_box.send_keys("\ue008\ue006")

        input_box.send_keys("\n")
        time.sleep(DELAYS["whatsapp_enter"])

    def send_pdf(self, pdf_path: str, message: Optional[str] = None) -> None:
        """Envía un archivo PDF."""
        if not self._chat_open:
            raise RuntimeError("No hay ningún chat abierto.")
        if not os.path.exists(pdf_path):
            logging.error(f"PDF no existe: {pdf_path}")
            raise FileNotFoundError(f"El archivo PDF no existe: {pdf_path}")
        if message:
            self.send_message(message)

        abs_path = os.path.abspath(pdf_path)

        try:
            clip = self.browser.find_first(WHATSAPP_SELECTORS["clip_button"])
            if clip is None:
                logging.error("No se encontró botón de adjuntar")
                raise RuntimeError("No se encontró el botón de adjuntar archivo. Verifica que WhatsApp esté cargado.")

            self.browser.action_click(clip)
            time.sleep(DELAYS["whatsapp_clip"])

            doc_clicked = False
            end = time.time() + TIMEOUTS["whatsapp_chat_open"]
            
            while time.time() < end and not doc_clicked:
                try:
                    for texto in ("Document", "Documento", "Fichier", "Datei"):
                        els = self.browser.find_all_xpath(f"//*[normalize-space(text())='{texto}']")
                        for el in els:
                            if self.browser.is_displayed(el):
                                self.browser.action_click(el)
                                doc_clicked = True
                                break
                        if doc_clicked:
                            break
                except Exception:
                    pass
                if not doc_clicked:
                    time.sleep(DELAYS["whatsapp_doc_click"])

            if not doc_clicked:
                logging.error("No se encontró opción Document")
                raise RuntimeError("No se encontró la opción de documento. Verifica que WhatsApp esté actualizado.")

            file_input = None
            end = time.time() + TIMEOUTS["file_input"]
            
            while time.time() < end:
                try:
                    all_inputs = self.browser.find_all_css("input[type='file']")
                    for inp in all_inputs:
                        accept = self.browser.get_element_attribute(inp, "accept").lower().strip()
                        if "image" not in accept:
                            file_input = inp
                            break
                except Exception:
                    pass
                if file_input is not None:
                    break
                time.sleep(DELAYS["whatsapp_doc_click"])

            if file_input is None:
                logging.error("No apareció input de documentos")
                raise RuntimeError("No se pudo cargar el selector de archivos.")

            try:
                file_input.send_keys(abs_path)
            except Exception:
                try:
                    self.browser.run_js("arguments[0].style.display='block';", file_input)
                    file_input.send_keys(abs_path)
                except Exception as e:
                    logging.error(f"No se pudo adjuntar PDF: {e}", exc_info=True)
                    raise RuntimeError("No se pudo adjuntar el archivo PDF.")

            time.sleep(DELAYS["whatsapp_file_attach"])
            self.browser.press_system_key("escape")
            time.sleep(DELAYS["whatsapp_escape"])

            time.sleep(DELAYS["whatsapp_send"])
            self.browser.press_enter()
            time.sleep(DELAYS["whatsapp_escape"])

        except RuntimeError:
            raise
        except FileNotFoundError:
            raise
        except Exception as e:
            logging.error(f"Error enviando PDF: {e}", exc_info=True)
            raise RuntimeError("Error al enviar el PDF por WhatsApp.")

    def send_to(self, phone_number: str, message: str, pdf_path: str) -> None:
        """Flujo completo: abre chat, envía mensaje y PDF."""
        self.open_chat(phone_number)
        self.send_message(message)
        self.send_pdf(pdf_path)
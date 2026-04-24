# services/whatsapp_web.py
from __future__ import annotations

import os
import time
from typing import Optional

from config import WA_URL, WA_SELECTORS
from tools.browser import BrowserTools


class WhatsAppService:

    def __init__(
        self,
        browser: BrowserTools | None = None,
        default_timeout: int = 10,
    ):
        self.browser = browser or BrowserTools()
        self.default_timeout = default_timeout
        self._chat_open = False

    # ─────────────────────────────────────────
    # Sesión
    # ─────────────────────────────────────────

    def start_session(self) -> None:
        if not self.browser.is_active():
            self.browser.start()
        self.browser.go_to(WA_URL)
        self.browser.wait_for("tag", "body", timeout=30)

    def close_session(self) -> None:
        self.browser.close()
        self._chat_open = False

    def is_logged_in(self) -> bool:
        """URL OR cookies OR DOM — cualquiera de las tres basta."""
        try:
            driver = self.browser.driver
            if driver is None:
                return False

            url_ok = False
            try:
                url_ok = "web.whatsapp.com" in (driver.current_url or "")
            except Exception:
                url_ok = False

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
                dom_checks = [
                    "div[contenteditable='true'][data-tab='3']",
                    "div[contenteditable='true'][data-tab='10']",
                    "div[data-testid='pane-side']",
                    "div[data-testid='conversation-panel']",
                ]
                for sel in dom_checks:
                    if self.browser.find_all_css(sel):
                        dom_ok = True
                        break
            except Exception:
                dom_ok = False

            return url_ok or cookies_ok or dom_ok

        except Exception:
            return False

    # ─────────────────────────────────────────
    # Chat
    # ─────────────────────────────────────────

    def open_chat(self, phone_number: str) -> None:
        if not self.is_logged_in():
            raise RuntimeError("WhatsApp Web no está activo. Ábrelo primero.")

        phone = str(phone_number).strip().lstrip("+")

        opened = self._open_chat_by_search(phone)
        if not opened:
            opened = self._open_chat_by_url(phone)

        if not opened:
            raise RuntimeError(
                f"No se pudo abrir el chat con {phone_number}. "
                "Verifica que el número esté guardado o que la sesión esté activa."
            )

        self._chat_open = True

    # ─────────────────────────────────────────
    # Helpers internos
    # ─────────────────────────────────────────

    def _conversation_is_open(self, search_field=None) -> bool:
        try:
            for sel in WA_SELECTORS["conversation_panel"]:
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
        for sel in WA_SELECTORS["chat_input"]:
            try:
                boxes = self.browser.find_all_css(sel)
                for b in boxes:
                    if self.browser.is_displayed(b) and self.browser.get_size(b).get("height", 0) > 8:
                        return b
            except Exception:
                continue

        # Fallback: contenteditable más grande visible
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

    # ─────────────────────────────────────────
    # Estrategias para abrir chat
    # ─────────────────────────────────────────

    def _open_chat_by_search(self, phone: str) -> bool:
        search_field = None
        end = time.time() + 4.0
        while time.time() < end and search_field is None:
            search_field = self.browser.find_first(WA_SELECTORS["search_inputs"])
            if search_field is None:
                time.sleep(0.2)

        if search_field is None:
            return False

        try:
            self.browser.focus_and_scroll(search_field)
            try:
                search_field.click()
            except Exception:
                self.browser.run_js("arguments[0].click();", search_field)

            self.browser.clear_and_type(search_field, phone)
            time.sleep(0.6)

            self.browser.send_keys_to(search_field, "\n")

            end2 = time.time() + 3.0
            while time.time() < end2:
                if self._conversation_is_open(search_field):
                    return True
                time.sleep(0.2)

            # ENTER no abrió — clicar primer resultado
            for result_sel in ("div[role='option']", "div[role='button'][data-testid]"):
                try:
                    els = self.browser.find_all_css(result_sel)
                    if els:
                        els[0].click()
                        time.sleep(0.6)
                        if self._conversation_is_open(search_field):
                            return True
                except Exception:
                    pass

        except Exception:
            pass

        return False

    def _open_chat_by_url(self, phone: str) -> bool:
        try:
            self.browser.go_to(f"{WA_URL}send?phone={phone}")
            self.browser.wait_until(lambda d: self.is_logged_in(), timeout=8)
            time.sleep(0.8)
            end = time.time() + 5.0
            while time.time() < end:
                if self._conversation_is_open():
                    return True
                time.sleep(0.4)
        except Exception:
            pass
        return False

    # ─────────────────────────────────────────
    # Mensaje de texto
    # ─────────────────────────────────────────

    def send_message(self, message: str) -> None:
        if not self._chat_open:
            raise RuntimeError("No hay chat abierto.")

        input_box = self._find_chat_input()
        if input_box is None:
            raise RuntimeError("No se encontró el campo de texto del chat.")

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
                input_box.send_keys("\ue008\ue006")  # SHIFT+ENTER

        input_box.send_keys("\n")
        time.sleep(0.35)

    # ─────────────────────────────────────────
    # PDF
    # ─────────────────────────────────────────

    def send_pdf(self, pdf_path: str, message: Optional[str] = None) -> None:
        if not self._chat_open:
            raise RuntimeError("No hay chat abierto.")
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF no existe: {pdf_path}")
        if message:
            self.send_message(message)

        abs_path = os.path.abspath(pdf_path)

        # 1. Abrir submenú con action_click (mantiene foco en navegador)
        clip = self.browser.find_first(WA_SELECTORS["clip_button"])
        if clip is None:
            raise RuntimeError("No se encontró el botón de adjuntar archivo.")

        self.browser.action_click(clip)
        time.sleep(0.8)

        # 2. Clicar Document del submenú
        doc_clicked = False
        end = time.time() + 5.0
        while time.time() < end and not doc_clicked:
            try:
                for texto in ("Document", "Documento", "Fichier", "Datei"):
                    els = self.browser.find_all_xpath(
                        f"//*[normalize-space(text())='{texto}']"
                    )
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
                time.sleep(0.2)

        if not doc_clicked:
            raise RuntimeError("No se encontró la opción Document en el submenú.")

        # 3. Esperar input de documentos (accept="*", no imágenes)
        file_input = None
        end = time.time() + 6.0
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
            time.sleep(0.2)

        if file_input is None:
            raise RuntimeError("No apareció el input de documentos.")

        # 4. Enviar ruta al input
        try:
            file_input.send_keys(abs_path)
        except Exception:
            try:
                self.browser.run_js("arguments[0].style.display='block';", file_input)
                file_input.send_keys(abs_path)
            except Exception as e:
                raise RuntimeError(f"No se pudo adjuntar el PDF: {e}")

        # 5. Cerrar explorador de archivos con Escape del sistema
        time.sleep(2.0)
        self.browser.press_system_key("escape")
        time.sleep(1.0)

        # 6. Esperar preview y enviar con Enter
        time.sleep(2.0)
        self.browser.press_enter()
        time.sleep(1.0)

    # ─────────────────────────────────────────
    # Flujo completo
    # ─────────────────────────────────────────

    def send_to(self, phone_number: str, message: str, pdf_path: str) -> None:
        self.open_chat(phone_number)
        self.send_message(message)
        self.send_pdf(pdf_path)
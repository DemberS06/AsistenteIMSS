# services/whatsapp_web.py
from __future__ import annotations

import math
import os
import time
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from tools.browser import BrowserTools


class WhatsAppService:

    URL = "https://web.whatsapp.com/"

    SELECTORS = {
        "search_inputs": [
            "input[aria-label='Search or start a new chat']",
            "input[aria-label='Buscar o iniciar un chat']",
            "input[role='textbox'][data-tab='3']",
            "input[placeholder='Search or start a new chat']",
            # Fallbacks viejos por si acaso
            "div[contenteditable='true'][data-tab='3']",
            "div[title='Buscar o iniciar un chat']",
        ],
        "conversation_panel": [
            "div[data-testid='conversation-panel']",
            "div[role='application']",
        ],
        "chat_input": [
            "div[contenteditable='true'][data-tab='10']",
            "div[contenteditable='true'][data-tab='6']",
        ],
        "clip_button": [
            "button[title='Attach']",
            "span[data-icon='plus-rounded']",
            "span[data-testid='clip']",
        ],
        "file_input": [
            "input[type='file']",
        ],
        "send_button": [
            "span[data-icon='send']",
            "button[data-testid='compose-btn-send']",
            "button[aria-label='Send']",
            "button[aria-label='Enviar']",
            "span[data-icon='wds-ic-send-filled']",
            "button[data-tab='11']",
        ],
    }

    _SEND_POSITIVE = ("send", "wds-ic-send", "wds-ic-send-filled", "compose-btn-send", "enviar")
    _SEND_NEGATIVE = ("mic", "microphone", "record", "audio", "voice", "grab",
                      "micro", "recording", "grabación", "audio-record", "mic-fill")

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
        self.browser.go_to(self.URL)
        self.browser.wait_for(By.TAG_NAME, "body", timeout=30)

    def close_session(self) -> None:
        self.browser.close()
        self._chat_open = False

    def is_logged_in(self) -> bool:
        """
        URL OR cookies OR DOM — cualquiera de las tres basta.
        """
        try:
            driver = self.browser._driver
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
                    if driver.find_elements(By.CSS_SELECTOR, sel):
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

    def _driver(self):
        return self.browser._driver

    def _find_first(self, selectors: list[str]):
        driver = self._driver()
        if driver is None:
            return None
        for sel in selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    return els[0]
            except Exception:
                continue
        return None

    def _click_first(self, selectors: list[str]) -> bool:
        el = self._find_first(selectors)
        if el is None:
            return False
        try:
            el.click()
            return True
        except Exception:
            try:
                self._driver().execute_script("arguments[0].click();", el)
                return True
            except Exception:
                return False

    def _conversation_is_open(self, search_field=None) -> bool:
        driver = self._driver()
        if driver is None:
            return False
        try:
            for sel in self.SELECTORS["conversation_panel"]:
                try:
                    if driver.find_elements(By.CSS_SELECTOR, sel):
                        return True
                except Exception:
                    continue

            all_inputs = driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
            for el in all_inputs:
                try:
                    if search_field is not None:
                        same = driver.execute_script(
                            "return arguments[0] === arguments[1];", el, search_field
                        )
                        if same:
                            continue
                    size = el.size
                    if size and size.get("height", 0) > 10 and size.get("width", 0) > 10:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _find_chat_input(self):
        driver = self._driver()
        if driver is None:
            return None

        for sel in self.SELECTORS["chat_input"]:
            try:
                boxes = driver.find_elements(By.CSS_SELECTOR, sel)
                for b in boxes:
                    try:
                        if b.is_displayed() and b.size.get("height", 0) > 8:
                            return b
                    except Exception:
                        continue
            except Exception:
                continue

        # Fallback: contenteditable más grande visible
        try:
            all_inputs = driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
            max_area, candidate = 0, None
            for el in all_inputs:
                try:
                    if not el.is_displayed():
                        continue
                    s = el.size
                    area = s.get("height", 0) * s.get("width", 0)
                    if area > max_area and s.get("height", 0) > 8:
                        candidate, max_area = el, area
                except Exception:
                    continue
            return candidate
        except Exception:
            return None

    def _find_send_button_for_pdf(self, file_input) -> object | None:
        driver = self._driver()
        if driver is None:
            return None

        try:
            fi_loc  = file_input.location
            fi_size = file_input.size
            fi_cx   = fi_loc.get("x", 0) + fi_size.get("width", 0) / 2.0
            fi_cy   = fi_loc.get("y", 0) + fi_size.get("height", 0) / 2.0
        except Exception:
            fi_cx = fi_cy = 0

        def _dist(el) -> float:
            try:
                loc  = el.location
                size = el.size
                cx = loc.get("x", 0) + size.get("width", 0) / 2.0
                cy = loc.get("y", 0) + size.get("height", 0) / 2.0
                return math.hypot(cx - fi_cx, cy - fi_cy)
            except Exception:
                return float("inf")

        candidates = []
        for sel in self.SELECTORS["send_button"]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                els = []
            for el in els:
                try:
                    if not el.is_displayed():
                        continue
                    aria      = (el.get_attribute("aria-label") or "").lower()
                    data_icon = (el.get_attribute("data-icon")   or "").lower()
                    title     = (el.get_attribute("title")       or "").lower()
                    inner     = (el.text                         or "").lower()
                    blob      = " ".join([aria, data_icon, title, inner])
                    if any(tok in blob for tok in self._SEND_NEGATIVE):
                        continue
                    pos_score = 1 if any(tok in blob for tok in self._SEND_POSITIVE) else 0
                    candidates.append({"el": el, "pos_score": pos_score, "dist": _dist(el)})
                except Exception:
                    continue

        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x["pos_score"], x["dist"]))
        return candidates[0]["el"]

    # ─────────────────────────────────────────
    # Estrategias para abrir chat
    # ─────────────────────────────────────────

    def _open_chat_by_search(self, phone: str) -> bool:
        driver = self._driver()

        print(f"[WA] URL actual del driver: {driver.current_url}")

        search_field = None
        end = time.time() + 4.0
        while time.time() < end and search_field is None:
            search_field = self._find_first(self.SELECTORS["search_inputs"])
            if search_field is None:
                time.sleep(0.2)

        print(f"[WA] search_field encontrado: {search_field is not None}")
        if search_field is None:
            print("[WA] Campo de búsqueda no encontrado.")
            return False

        print(f"[WA] search_field tag: {search_field.tag_name}, displayed: {search_field.is_displayed()}")

        try:
            driver.execute_script(
                "arguments[0].scrollIntoView(true); arguments[0].focus();", search_field
            )
            try:
                search_field.click()
            except Exception:
                driver.execute_script("arguments[0].click();", search_field)

            try:
                search_field.send_keys(Keys.CONTROL + "a")
                search_field.send_keys(Keys.BACKSPACE)
            except Exception:
                pass

            try:
                search_field.send_keys(phone)
            except Exception:
                driver.execute_script(
                    "arguments[0].innerText = arguments[1]; "
                    "arguments[0].dispatchEvent(new Event('input'));",
                    search_field, phone
                )

            time.sleep(0.6)

            print(f"[WA] Después de escribir — conversation_is_open: {self._conversation_is_open(search_field)}")

            for sel in ("div[role='option']", "div[role='button'][data-testid]", "div[aria-label]"):
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                visible = [e for e in els if e.is_displayed()]
                print(f"[WA] Selector '{sel}': {len(visible)} visibles")

            try:
                search_field.send_keys(Keys.ENTER)
            except Exception:
                pass

            end2 = time.time() + 3.0
            while time.time() < end2:
                if self._conversation_is_open(search_field):
                    print("[WA] Chat abierto por búsqueda.")
                    return True
                time.sleep(0.2)

            print(f"[WA] Después de ENTER — conversation_is_open: {self._conversation_is_open(search_field)}")

            for result_sel in ("div[role='option']", "div[role='button'][data-testid]"):
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, result_sel)
                    if els:
                        print(f"[WA] Clicando resultado con selector '{result_sel}'")
                        els[0].click()
                        time.sleep(0.6)
                        if self._conversation_is_open(search_field):
                            print("[WA] Chat abierto clicando resultado.")
                            return True
                except Exception:
                    pass

        except Exception as e:
            print(f"[WA] Error en búsqueda: {e}")

        print("[WA] _open_chat_by_search falló.")
        return False
        
    def _open_chat_by_url(self, phone: str) -> bool:
        try:
            url = f"https://web.whatsapp.com/send?phone={phone}"
            print(f"[WA] Fallback URL: {url}")
            self.browser.go_to(url)
            try:
                WebDriverWait(self._driver(), 8).until(lambda d: self.is_logged_in())
            except Exception:
                pass
            time.sleep(0.8)
            end = time.time() + 5.0
            while time.time() < end:
                if self._conversation_is_open():
                    print("[WA] Chat abierto por URL.")
                    return True
                time.sleep(0.4)
        except Exception as e:
            print(f"[WA] Fallback URL falló: {e}")
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
                self._driver().execute_script("arguments[0].focus();", input_box)
            except Exception:
                pass

        lines = str(message).splitlines()
        for i, line in enumerate(lines):
            input_box.send_keys(line)
            if i < len(lines) - 1:
                input_box.send_keys(Keys.SHIFT + Keys.ENTER)

        input_box.send_keys(Keys.ENTER)
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

        driver = self._driver()
        abs_path = os.path.abspath(pdf_path)

        from selenium.webdriver.common.action_chains import ActionChains
        import pyautogui

        # 1. Abrir submenú con ActionChains (mantiene foco en navegador)
        clip = self._find_first(self.SELECTORS["clip_button"])
        if clip is None:
            raise RuntimeError("No se encontró el botón de adjuntar archivo.")

        ActionChains(driver).move_to_element(clip).click().perform()
        time.sleep(0.8)

        # 2. Clicar Document con ActionChains usando XPATH por texto
        doc_clicked = False
        end = time.time() + 5.0
        while time.time() < end and not doc_clicked:
            try:
                for texto in ("Document", "Documento", "Fichier", "Datei"):
                    els = driver.find_elements(By.XPATH,
                        f"//*[normalize-space(text())='{texto}']"
                    )
                    for el in els:
                        if el.is_displayed():
                            ActionChains(driver).move_to_element(el).click().perform()
                            doc_clicked = True
                            print(f"[WA] Clic en '{texto}' con ActionChains.")
                            break
                    if doc_clicked:
                        break
            except Exception:
                pass
            if not doc_clicked:
                time.sleep(0.2)

        if not doc_clicked:
            raise RuntimeError("No se encontró la opción Document en el submenú.")

        # 3. Esperar input de documentos (accept="*")
        file_input = None
        end = time.time() + 6.0
        while time.time() < end:
            try:
                all_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                for inp in all_inputs:
                    accept = (inp.get_attribute("accept") or "").lower().strip()
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
                driver.execute_script("arguments[0].style.display='block';", file_input)
                file_input.send_keys(abs_path)
            except Exception as e:
                raise RuntimeError(f"No se pudo adjuntar el PDF: {e}")

        # 5. Cerrar el explorador de archivos con Escape del sistema
        time.sleep(2.0)
        pyautogui.press("escape")
        time.sleep(1.0)

        # 6. Esperar preview y enviar con Enter del navegador
        time.sleep(2.0)
        self.browser.press(Keys.ENTER)
        time.sleep(1.0)

    # ─────────────────────────────────────────
    # Flujo completo
    # ─────────────────────────────────────────

    def send_to(self, phone_number: str, message: str, pdf_path: str) -> None:
        """Abre chat, envía mensaje y adjunta PDF en un solo paso."""
        self.open_chat(phone_number)
        self.send_message(message)
        self.send_pdf(pdf_path)
# modules/whatsapp_manager.py
import os
import time
import traceback
from urllib.parse import quote

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class WhatsAppManager:
    def __init__(
        self,
        webmanager=None,
        profile_dir: str = None,
        headless: bool = False,
        temp_download_dir: str = None,
        default_wait: float = 6.0,
        qr_image_path: str = "whatsapp_qr.png",
    ):
        self.webmanager = webmanager
        self.driver = getattr(webmanager, "driver", None) if webmanager else None
        self.own_driver = False if self.driver else True

        self.profile_dir = os.path.abspath(profile_dir) if profile_dir else None
        self.headless = headless
        self.temp_download_dir = os.path.abspath(temp_download_dir) if temp_download_dir else None

        self.default_wait = float(default_wait)
        self.qr_image_path = qr_image_path
        self.selectors = {
            "conversation_panel": ["div[data-testid='conversation-panel']", "div[role='application']"],
            "search_inputs": [
                "div[contenteditable='true'][data-tab='3']",
                "div[title='Buscar o iniciar un chat']",
                "div[aria-label='Search input textbox']",
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
            "file_input": ["input[type='file']"],
            "send_button": ["span[data-icon='send']", "button[data-testid='compose-btn-send']"],
        }

    # ---------- driver lifecycle ----------
    def _create_driver(self):
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--safebrowsing-disable-download-protection")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        if self.temp_download_dir:
            prefs = {
                "download.default_directory": self.temp_download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
            }
            options.add_experimental_option("prefs", prefs)
        if self.profile_dir:
            options.add_argument(f"--user-data-dir={self.profile_dir}")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.own_driver = True
        return self.driver

    # ---------- session check (rápido, no bloqueante) ----------
    def check_session_active(self) -> bool:
        try:
            if self.driver is None:
                return False

            try:
                cur = self.driver.current_url or ""
            except Exception:
                cur = ""
            if "web.whatsapp.com" not in cur:
                url_ok = False
            else:
                url_ok = True

            cookies_ok = False
            try:
                ck = self.driver.get_cookies() or []
                if ck:
                    for c in ck:
                        dn = (c.get("domain") or "").lower()
                        nm = (c.get("name") or "").lower()
                        if "whatsapp" in dn or "whatsapp" in nm or ".whatsapp" in dn:
                            cookies_ok = True
                            break
                if not cookies_ok and len(ck) >= 2:
                    cookies_ok = True
            except Exception:
                cookies_ok = False

            dom_ok = False
            try:
                if self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']"):
                    dom_ok = True
                elif self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']"):
                    dom_ok = True
                elif self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='pane-side']"):
                    dom_ok = True
                elif self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='conversation-panel']"):
                    dom_ok = True
            except Exception:
                dom_ok = False

            return url_ok or cookies_ok or dom_ok
        except Exception:
            return False

    def open_whatsapp(self, wait_for_qr: float = None):
        wait_for_qr = wait_for_qr if wait_for_qr is not None else self.default_wait
        try:
            if self.driver is None:
                if self.webmanager and getattr(self.webmanager, "driver", None):
                    self.driver = self.webmanager.driver
                    self.own_driver = False
                else:
                    self._create_driver()

            if self.check_session_active():
                return {"status": "ok", "message": "WhatsApp Web listo."}

            try:
                self.driver.get("https://web.whatsapp.com/")
            except Exception:
                return {"status": "error", "message": "No se pudo navegar a web.whatsapp.com."}

            short = min(2.0, wait_for_qr, self.default_wait)
            try:
                WebDriverWait(self.driver, short).until(lambda d: self.check_session_active())
                return {"status": "ok", "message": "WhatsApp Web listo."}
            except Exception:
                try:
                    self.driver.save_screenshot(self.qr_image_path)
                except Exception:
                    pass
                return {"status": "needs_qr", "message": "Escanea el QR", "qr_path": self.qr_image_path}

        except Exception as e:
            return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

    # ---------- helpers rápidos (no bloqueantes) ----------
    def _find_first_present(self, selectors):
        if self.driver is None:
            return None
        for sel in selectors:
            try:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    return els[0]
            except Exception:
                continue
        return None

    def _click_if_present(self, selectors) -> bool:
        el = self._find_first_present(selectors)
        if el:
            try:
                el.click()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", el)
                    return True
                except Exception:
                    return False
        return False

    # ---------- abrir chat por búsqueda (sin recargar) ----------
    def _open_chat_by_search(self, phone_number: str) -> bool:
        try:
            if self.driver is None:
                print("[WAM] _open_chat_by_search: driver is None")
                return False

            pn_raw = str(phone_number or "").strip()
            if not pn_raw:
                print("[WAM] _open_chat_by_search: phone_number vacío")
                return False
           
            candidates = [pn_raw]
            
            seen = set()
            candidates = [c for c in candidates if not (c in seen or seen.add(c))]

            print(f"[WAM] _open_chat_by_search: candidates={candidates}")

            def conversation_open(search_field_elem=None):
                try:
                    for sel in self.selectors.get("conversation_panel", []):
                        if self.driver.find_elements(By.CSS_SELECTOR, sel):
                            return True
                    try:
                        all_inputs = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
                        if not all_inputs:
                            return False
                        for el in all_inputs:
                            try:
                                if search_field_elem is not None:
                                    try:
                                        same = self.driver.execute_script("return arguments[0] === arguments[1];", el, search_field_elem)
                                        if same:
                                            continue
                                    except Exception:
                                        pass
                                size = el.size
                                if size and size.get("height", 0) > 10 and size.get("width", 0) > 10:
                                    return True
                            except Exception:
                                continue
                    except Exception:
                        pass
                    return False
                except Exception:
                    return False

            search_field = None
            end = time.time() + 4.0
            while time.time() < end and search_field is None:
                search_field = self._find_first_present(self.selectors.get("search_inputs", []))
                if search_field is None:
                    time.sleep(0.2)

            if search_field is None:
                try:
                    cur = ""
                    try:
                        cur = self.driver.current_url or ""
                    except Exception:
                        cur = ""
                    if "web.whatsapp.com" not in cur:
                        try:
                            self.driver.get("https://web.whatsapp.com/")
                        except Exception:
                            pass
                    time.sleep(0.5)
                    search_field = self._find_first_present(self.selectors.get("search_inputs", []))
                except Exception:
                    pass

            if search_field is None:
                print("[WAM] _open_chat_by_search: no se encontró campo de búsqueda")
            else:
                print("[WAM] _open_chat_by_search: campo de búsqueda detectado")

            if search_field is not None:
                for cand in candidates:
                    try:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].focus();", search_field)
                        except Exception:
                            pass
                        try:
                            search_field.click()
                        except Exception:
                            try:
                                self.driver.execute_script("arguments[0].click();", search_field)
                            except Exception:
                                pass

                        try:
                            search_field.send_keys(Keys.CONTROL + "a")
                            search_field.send_keys(Keys.BACKSPACE)
                        except Exception:
                            pass

                        try:
                            search_field.send_keys(cand)
                        except Exception:
                            try:
                                self.driver.execute_script(
                                    "arguments[0].innerText = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                                    search_field, cand
                                )
                            except Exception:
                                pass

                        time.sleep(0.6)

                        try:
                            search_field.send_keys(Keys.ENTER)
                        except Exception:
                            pass

                        wait_until = time.time() + 3.0
                        while time.time() < wait_until:
                            if conversation_open(search_field):
                                print(f"[WAM] _open_chat_by_search: conversación abierta tras buscar '{cand}'")
                                return True
                            time.sleep(0.2)

                        for rs in ("div[role='option']", "div[role='button'][data-testid]"):
                            try:
                                els = self.driver.find_elements(By.CSS_SELECTOR, rs)
                                if els:
                                    try:
                                        els[0].click()
                                        time.sleep(0.6)
                                        if conversation_open(search_field):
                                            print(f"[WAM] _open_chat_by_search: conversación abierta tras clicar resultado para '{cand}'")
                                            return True
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                    except Exception:
                        continue

            try:
                wa_url = f"https://web.whatsapp.com/send?phone={phone_number}"
                print(f"[WAM] _open_chat_by_search: fallback wa.me -> {wa_url}")
                self.driver.get(wa_url)
                WebDriverWait(self.driver, 8).until(lambda d: conversation_open())
                time.sleep(0.8)
                if conversation_open():
                    print("[WAM] _open_chat_by_search: conversación abierta (fallback wa.me)")
                    return True
            except Exception as e:
                print("[WAM] _open_chat_by_search: fallback wa.me falló:", e)

            try:
                try:
                    self.driver.save_screenshot("whatsapp_debug.png")
                    print("[WAM] _open_chat_by_search: screenshot guardado -> whatsapp_debug.png")
                except Exception:
                    pass
                try:
                    src = getattr(self.driver, "page_source", None)
                    if src:
                        with open("whatsapp_debug.html", "w", encoding="utf-8") as fh:
                            fh.write(src[:500000])
                        print("[WAM] _open_chat_by_search: page_source guardado -> whatsapp_debug.html (recortado)")
                except Exception:
                    pass
            except Exception:
                pass

            print("[WAM] _open_chat_by_search: no se pudo abrir la conversación")
            return False

        except Exception as e:
            print("[WAM] _open_chat_by_search: excepción no manejada:", e)
            try:
                try:
                    self.driver.save_screenshot("whatsapp_debug_exception.png")
                    print("[WAM] _open_chat_by_search: screenshot guardado -> whatsapp_debug_exception.png")
                except Exception:
                    pass
                try:
                    src = getattr(self.driver, "page_source", None)
                    if src:
                        with open("whatsapp_debug_exception.html", "w", encoding="utf-8") as fh:
                            fh.write(src[:500000])
                        print("[WAM] _open_chat_by_search: page_source guardado -> whatsapp_debug_exception.html (recortado)")
                except Exception:
                    pass
            except Exception:
                pass
            return False

    # ---------- envío (texto primero, luego adjunto) ----------
    def send_message_with_pdf(self, phone_number: str, message: str, pdf_path: str, wait_for_qr: float = None):
        import traceback, time, math

        try:
            if not pdf_path or not os.path.exists(pdf_path):
                return {"status": "error", "message": f"PDF no existe: {pdf_path}"}

            if self.driver is None:
                if self.webmanager and getattr(self.webmanager, "driver", None):
                    self.driver = self.webmanager.driver
                    self.own_driver = False
                else:
                    return {"status": "error", "message": "Driver no inicializado. Abre WhatsApp Web primero con whatsapp.open_whatsapp()."}

            if not self.check_session_active():
                try:
                    self.driver.get("https://web.whatsapp.com/")
                    try:
                        self.driver.save_screenshot(self.qr_image_path)
                    except Exception:
                        pass
                except Exception:
                    pass
                return {"status": "needs_qr", "message": "Sesión no activa. Escanea el QR.", "qr_path": self.qr_image_path}

            pn = str(phone_number).strip()
            if pn.startswith("+"):
                pn = pn[1:]
            print(f"[WAM] send_message_with_pdf: abriendo chat para {pn}")

            opened = self._open_chat_by_search(pn)
            if not opened:
                try:
                    wa_url = f"https://web.whatsapp.com/send?phone={pn}"
                    print(f"[WAM] send_message_with_pdf: fallback abrir {wa_url}")
                    self.driver.get(wa_url)
                    WebDriverWait(self.driver, 8).until(lambda d: self.check_session_active())
                    time.sleep(0.8)
                except Exception as e:
                    print("[WAM] send_message_with_pdf: no se pudo abrir chat (fallback) ->", e)
                    return {"status": "error", "message": f"No se pudo abrir el chat para {phone_number} (búsqueda y fallback fallaron)."}

            input_box = None
            try:
                for sel in self.selectors.get("chat_input", []):
                    try:
                        boxes = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if boxes:
                            for b in boxes:
                                try:
                                    if b.is_displayed() and b.size.get("height", 0) > 8:
                                        input_box = b
                                        break
                                except Exception:
                                    continue
                        if input_box:
                            break
                    except Exception:
                        continue
                if input_box is None:
                    all_inputs = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
                    if all_inputs:
                        max_area = 0
                        candidate = None
                        for el in all_inputs:
                            try:
                                if not el.is_displayed():
                                    continue
                                s = el.size
                                area = s.get("height", 0) * s.get("width", 0)
                                if area > max_area and s.get("height", 0) > 8:
                                    candidate = el
                                    max_area = area
                            except Exception:
                                continue
                        input_box = candidate
            except Exception:
                input_box = None

            if message and message.strip():
                if input_box is None:
                    print("[WAM] send_message_with_pdf: no se encontró caja de texto; texto puede no enviarse ahora.")
                else:
                    try:
                        try:
                            input_box.click()
                        except Exception:
                            try:
                                self.driver.execute_script("arguments[0].focus();", input_box)
                            except Exception:
                                pass
                        lines = str(message).splitlines()
                        for i, line in enumerate(lines):
                            input_box.send_keys(line)
                            if i < len(lines) - 1:
                                input_box.send_keys(Keys.SHIFT + Keys.ENTER)
                        input_box.send_keys(Keys.ENTER)
                        time.sleep(0.35)
                        print("[WAM] send_message_with_pdf: texto enviado/puesto en caja.")
                    except Exception as e:
                        print("[WAM] send_message_with_pdf: error enviando texto:", e)

            try:
                print("[WAM] send_message_with_pdf: adjuntando PDF...")
                for clip_sel in self.selectors.get("clip_button", []):
                    try:
                        if self._click_if_present([clip_sel]):
                            break
                    except Exception:
                        continue

                file_input = None
                file_input = self._find_first_present(self.selectors.get("file_input", []))
                if file_input is None:
                    try:
                        file_input = WebDriverWait(self.driver, 6).until(
                            lambda d: self._find_first_present(self.selectors.get("file_input", []))
                        )
                    except Exception:
                        file_input = None
                if file_input is None:
                    try:
                        file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    except Exception:
                        file_input = None

                if file_input is None:
                    print("[WAM] send_message_with_pdf: no se encontró input[type='file']")
                    return {"status": "error", "message": "No se encontró input[type='file'] para adjuntar el PDF."}

                try:
                    file_input.send_keys(os.path.abspath(pdf_path))
                except Exception as e:
                    print("[WAM] send_message_with_pdf: file_input.send_keys falló ->", e)
                    try:
                        self.driver.execute_script("arguments[0].style.display='block';", file_input)
                        file_input.send_keys(os.path.abspath(pdf_path))
                    except Exception:
                        print("[WAM] send_message_with_pdf: fallback file_input JS falló")

                time.sleep(2)  # dejar cargar preview

                send_selectors = list(self.selectors.get("send_button", []))
                send_selectors.extend([
                    "button[aria-label='Send']",
                    "button[data-tab='11']",
                    "span[data-icon='wds-ic-send-filled']",
                    "button[aria-label='Enviar']",
                    "button[data-testid='compose-btn-send']"
                ])

                send_positive_tokens = ("send", "wds-ic-send", "wds-ic-send-filled", "compose-btn-send", "enviar")
                send_negative_tokens = ("mic", "microphone", "record", "audio", "voice", "grab", "micro", "recording", "grabación", "audio-record", "mic-fill")

                try:
                    fi_loc = file_input.location
                    fi_size = file_input.size
                    fi_center = (fi_loc.get("x", 0) + fi_size.get("width", 0)/2.0, fi_loc.get("y", 0) + fi_size.get("height", 0)/2.0)
                except Exception:
                    fi_center = (0, 0)

                def _distance_to_file_input(el):
                    try:
                        loc = el.location
                        size = el.size
                        cx = loc.get("x", 0) + size.get("width", 0)/2.0
                        cy = loc.get("y", 0) + size.get("height", 0)/2.0
                        return math.hypot(cx - fi_center[0], cy - fi_center[1])
                    except Exception:
                        return float("inf")

                candidates = []
                for sb in send_selectors:
                    try:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sb)
                    except Exception:
                        els = []
                    for el in els:
                        try:
                            if not el.is_displayed():
                                continue
                            aria = ""
                            data_icon = ""
                            title = ""
                            inner = ""
                            try:
                                aria = (el.get_attribute("aria-label") or "").lower()
                            except Exception:
                                aria = ""
                            try:
                                data_icon = (el.get_attribute("data-icon") or "").lower()
                            except Exception:
                                data_icon = ""
                            try:
                                title = (el.get_attribute("title") or "").lower()
                            except Exception:
                                title = ""
                            try:
                                inner = (el.text or "").lower()
                            except Exception:
                                inner = ""

                            attr_blob = " ".join([aria, data_icon, title, inner])

                            if any(tok in attr_blob for tok in send_negative_tokens):
                                continue

                            pos_score = 1 if any(tok in attr_blob for tok in send_positive_tokens) else 0

                            dist = _distance_to_file_input(el)
                            candidates.append({"el": el, "selector": sb, "pos_score": pos_score, "dist": dist, "blob": attr_blob})
                        except Exception:
                            continue

                candidates_sorted = sorted(candidates, key=lambda x: (-x["pos_score"], x["dist"]))

                send_btn = None
                send_btn_selector = None
                if candidates_sorted:
                    chosen = candidates_sorted[0]
                    send_btn = chosen["el"]
                    send_btn_selector = chosen.get("selector")
                    print(f"[WAM] send_message_with_pdf: candidato send elegido: selector={send_btn_selector}, dist={chosen['dist']:.1f}, blob={chosen['blob'][:120]}")

                if send_btn is None:
                    print("[WAM] send_message_with_pdf: no se detectó botón send confiable, usar ENTER fallback muy breve")
                    try:
                        if input_box:
                            input_box.send_keys(Keys.ENTER)
                            time.sleep(0.6)
                        else:
                            try:
                                self.driver.save_screenshot("whatsapp_debug.png")
                                src = getattr(self.driver, "page_source", None)
                                if src:
                                    with open("whatsapp_debug.html", "w", encoding="utf-8") as fh:
                                        fh.write(src[:500000])
                                print("[WAM] send_message_with_pdf: debug artifacts saved (no send candidate).")
                            except Exception:
                                pass
                            return {"status": "error", "message": "No se detectó botón de envío confiable y no hay caja para fallback ENTER."}
                    except Exception as e:
                        print("[WAM] send_message_with_pdf: ENTER fallback falló:", e)
                        try:
                            self.driver.save_screenshot("whatsapp_debug.png")
                            src = getattr(self.driver, "page_source", None)
                            if src:
                                with open("whatsapp_debug.html", "w", encoding="utf-8") as fh:
                                    fh.write(src[:500000])
                        except Exception:
                            pass
                        return {"status": "error", "message": f"Intento de fallback ENTER falló: {e}"}

                clicked = False
                try:
                    send_btn.click()
                    clicked = True
                    print("[WAM] send_message_with_pdf: click normal en send intentado.")
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", send_btn)
                        clicked = True
                        print("[WAM] send_message_with_pdf: click JS en send intentado.")
                    except Exception:
                        try:
                            self.driver.execute_script(
                                "var ev = new MouseEvent('click', {bubbles:true,cancelable:true,view:window}); arguments[0].dispatchEvent(ev);",
                                send_btn
                            )
                            clicked = True
                            print("[WAM] send_message_with_pdf: dispatchEvent click en send intentado.")
                        except Exception:
                            clicked = False

                time.sleep(1)

                err_text = None
                try:
                    alert_selectors = ("div[role='alert']", "div[aria-live='assertive']", "div[aria-live='polite']", "div[data-testid='toast-container']")
                    for sel in alert_selectors:
                        try:
                            els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                            if els:
                                for el in els:
                                    try:
                                        txt = (el.text or "").strip()
                                        if txt:
                                            low = txt.lower()
                                            if any(k in low for k in ("not supported", "archive not supported", "no soport", "archivo no", "no se puede", "not support")):
                                                err_text = txt
                                                break
                                    except Exception:
                                        continue
                            if err_text:
                                break
                        except Exception:
                            continue

                    if not err_text:
                        ps = (self.driver.page_source or "")[:20000].lower()
                        for needle in ("not supported", "archive not supported", "no soport", "archivo no", "no se puede", "not support"):
                            if needle in ps:
                                start = ps.find(needle)
                                snippet = ps[max(0, start-80): start+len(needle)+120]
                                err_text = f"UI snippet: ...{snippet}..."
                                break
                except Exception:
                    pass

                if err_text:
                    return {"status": "error", "message": f"WhatsApp UI error after send attempt: {err_text}"}

            except Exception as e:
                print("[WAM] send_message_with_pdf: excepción adjuntando/enviando PDF:", e)
                try:
                    self.driver.save_screenshot("whatsapp_debug_exception.png")
                    src = getattr(self.driver, "page_source", None)
                    if src:
                        with open("whatsapp_debug_exception.html", "w", encoding="utf-8") as fh:
                            fh.write(src[:500000])
                    print("[WAM] send_message_with_pdf: debug artifacts saved (exception).")
                except Exception:
                    pass
                return {"status": "error", "message": f"Error adjuntando/enviando PDF: {e}", "trace": traceback.format_exc()}

            return {"status": "ok", "message": "Enviado (texto + PDF)."}
        except Exception as e:
            try:
                self.driver.save_screenshot("whatsapp_debug_outer_exception.png")
                src = getattr(self.driver, "page_source", None)
                if src:
                    with open("whatsapp_debug_outer_exception.html", "w", encoding="utf-8") as fh:
                        fh.write(src[:500000])
            except Exception:
                pass
            return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

    # ---------- cleanup ----------
    def quit(self):
        if self.own_driver and self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
                self.own_driver = False

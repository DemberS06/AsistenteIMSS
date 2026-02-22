# modules/web_management.py
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class WebManager:
    def __init__(self, headless=False, temp_download_dir=None):
        self.driver = None
        self.headless = headless
        self.temp_download_dir = os.path.abspath(temp_download_dir or os.path.join(os.getcwd(), "_tmp_downloads"))
        os.makedirs(self.temp_download_dir, exist_ok=True)
        self.download_folder = None  

    def set_download_folder(self, folder_path):
        self.download_folder = os.path.abspath(folder_path)

    def open_page(self, url, timeout=15):
        try:
            if self.driver is None:
                options = webdriver.ChromeOptions()
                if self.headless:
                    options.add_argument("--headless=new")
                    options.add_argument("--disable-gpu")
                options.add_argument("--start-maximized")

                prefs = {
                    "download.default_directory": self.temp_download_dir,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "plugins.always_open_pdf_externally": True,  
                    "profile.default_content_setting_values.automatic_downloads": 1,
                    "profile.default_content_settings.popups": 0
                }
                options.add_experimental_option("prefs", prefs)

                options.add_argument("--disable-popup-blocking")
                options.add_argument("--safebrowsing-disable-download-protection")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])

                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=options
                )
            self.driver.get(url)
            
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True
        except Exception as e:
            print(f"[WebManager] Error abriendo página: {e}")
            return False

    def get_captcha_screenshot(self, element_id="captchaImg", timeout=15):
        if self.driver is None:
            raise Exception("Driver no inicializado")
        el = WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((By.ID, element_id)))
        time.sleep(0.2)  # dejar un momento para render
        if el.size['width'] == 0 or el.size['height'] == 0:
            raise Exception("Captcha no renderizado correctamente")
        return el.screenshot_as_png

    def fill_form(self, fields: dict, wait=10):
        if self.driver is None:
            raise Exception("Driver no inicializado")
        for fid, val in fields.items():
            el = WebDriverWait(self.driver, wait).until(EC.presence_of_element_located((By.ID, fid)))
            try:
                el.clear()
            except Exception:
                pass
            el.send_keys(val)

    def click_button(self, button_id: str, wait=10):
        if self.driver is None:
            raise Exception("Driver no inicializado")
        btn = WebDriverWait(self.driver, wait).until(EC.element_to_be_clickable((By.ID, button_id)))
        btn.click()

    def wait_for_downloads(self, timeout=30, poll=0.25):
        end = time.time() + timeout
        while time.time() < end:
            try:
                entries = os.listdir(self.temp_download_dir)
            except FileNotFoundError:
                entries = []
            still = any(name.endswith(".crdownload") for name in entries)
            if not still:
                return True
            time.sleep(poll)
        return False

    def fill_form_and_validate(self, fields: dict, wait: float = 1.0):
        import traceback, time

        result = {"status": "driver_error", "errors": {}, "message": "", "exception": None}
        try:
            if self.driver is None:
                result["status"] = "driver_error"
                result["message"] = "Driver no inicializado."
                return result

            if not isinstance(fields, dict):
                result["status"] = "driver_error"
                result["message"] = "Fields inválidos (se esperaba dict)."
                return result
            try:
                self.fill_form(fields, wait=max(0.5, wait))
            except Exception as e:
                result["status"] = "driver_error"
                result["message"] = f"Error rellenando formulario: {e}"
                result["exception"] = traceback.format_exc()
                return result

            pre_error_ids = ["errorCurp", "errorRfc", "errorNss", "errorEmail"]
            errors = {}
            for eid in pre_error_ids:
                try:
                    elem = WebDriverWait(self.driver, 1).until(EC.visibility_of_element_located((By.ID, eid)))
                    text = elem.text.strip()
                    if text:
                        errors[eid] = text
                except Exception:
                    pass

            if errors:
                result["status"] = "field_error"
                result["errors"] = errors
                result["message"] = "Errores de validación en campos del formulario."
                return result

            try:
                self.click_button("continuar", wait=2)
            except Exception as e:
                result["status"] = "click_failed"
                result["message"] = f"No se pudo pulsar 'continuar': {e}"
                result["exception"] = traceback.format_exc()
                return result

            try:
                elem = WebDriverWait(self.driver, 1).until(EC.visibility_of_element_located((By.ID, "errorForm")))
                txt = elem.text.strip()
                if txt:
                    result["status"] = "form_error"
                    result["message"] = txt
                    return result
            except Exception:
                pass

            result["status"] = "ok"
            result["message"] = "Formulario enviado sin errores detectados."
            return result

        except Exception as e:
            result["status"] = "driver_error"
            result["message"] = str(e)
            result["exception"] = traceback.format_exc()
            return result

    def complete_registration(self, wait_per_click: float = 1.0):
        import time, traceback
        seq = ["submitContinuar", "continuar", "checkRenovacionAut", "terminos", "continuar", "guarda"]
        result = {"status": "error", "message": "No intentado", "details": []}
        try:
            if self.driver is None:
                result["status"] = "error"
                result["message"] = "Driver no inicializado"
                return result

            for btn_id in seq:
                try:
                    btn = WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, btn_id)))
                except Exception:
                    result["status"] = "already_registered"
                    result["message"] = f"Elemento esperado '{btn_id}' no encontrado en su turno — asumiendo que ya estaba registrado."
                    result["details"] = [f"Faltó botón: {btn_id}"]
                    self.click_button("salir")
                    return result

                try:
                    btn.click()
                    time.sleep(wait_per_click)
                except Exception as e:
                    result["status"] = "error"
                    result["message"] = f"Error al clickear '{btn_id}': {e}"
                    result["details"] = [traceback.format_exc()]
                    return result

            result["status"] = "ok"
            result["message"] = "Secuencia de registro ejecutada (revisar UI para confirmar)."
            result["details"] = []
            return result

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            result["details"] = [traceback.format_exc()]
            return result

    def initiate_pdf_downloads(self, click_count: int = 2, wait_timeout: int = 30, css_selector: str = "span.glyphicon.glyphicon-file"):
        import time, traceback, os
        result = {"status": "error", "temp_files": [], "message": "", "exception": None}
        try:
            if self.driver is None:
                result["status"] = "error"
                result["message"] = "Driver no inicializado"
                return result
            
            try:
                el = WebDriverWait(self.driver, 1).until(
                    EC.element_to_be_clickable((By.ID, "submitCancelar"))
                )
                el.click()  
                result["status"] = "no_registred"    
                result["message"] = "No ha sido registrado aún."
                return result
            except:
                pass

            icons = self.find_pdf_icons(css_selector=css_selector)
            if not icons:
                result["status"] = "no_icons"
                result["message"] = "No se encontraron iconos PDF en la página."
                return result

            for i in range(min(click_count, len(icons))):
                try:
                    icons[i].click()
                    time.sleep(0.2)
                except Exception:
                    try:
                        icons = self.find_pdf_icons(css_selector=css_selector)
                        if len(icons) > i:
                            icons[i].click()
                            time.sleep(0.2)
                    except Exception:
                        pass

            ok = self.wait_for_downloads(timeout=wait_timeout)
            time.sleep(0.5)

            try:
                entries = os.listdir(self.temp_download_dir)
            except Exception:
                entries = []

            result["temp_files"] = [f for f in entries if not f.endswith(".crdownload")]
            result["status"] = "ok" if ok else "wait_failed"
            if not ok:
                result["message"] = "Timeout esperando descargas."
            return result
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            result["exception"] = traceback.format_exc()
            return result

    def find_pdf_icons(self, css_selector="span.glyphicon.glyphicon-file"):
        if self.driver is None:
            return []
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, css_selector)
        except Exception:
            return []

    def refresh(self):
        if self.driver:
            self.driver.refresh()

    def quit(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        finally:
            self.driver = None
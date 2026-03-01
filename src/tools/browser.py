# tools/browser.py
from __future__ import annotations

from typing import Callable, Any, Iterable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException


class BrowserTools:
    def __init__(
        self,
        headless: bool = False,
        user_data_dir: str | None = None,
        profile_directory: str | None = None,
        download_dir: str | None = None,
        extra_options: Iterable[str] | None = None,
        driver: webdriver.Chrome | None = None,
    ):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.profile_directory = profile_directory
        self.download_dir = download_dir
        self.extra_options = list(extra_options) if extra_options else []
        self._driver = driver

    # =====================
    # lifecycle
    # =====================

    def start(self) -> None:
        if self._driver is not None:
            return

        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")

        if self.user_data_dir:
            options.add_argument(f"--user-data-dir={self.user_data_dir}")

        if self.profile_directory:
            options.add_argument(f"--profile-directory={self.profile_directory}")

        if self.download_dir:
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
            }
            options.add_experimental_option("prefs", prefs)

        for opt in self.extra_options:
            options.add_argument(opt)

        self._driver = webdriver.Chrome(options=options)

    def close(self) -> None:
        if self._driver:
            self._driver.quit()
            self._driver = None

    # =====================
    # navigation
    # =====================

    def go_to(self, url: str) -> None:
        self._require_driver()
        self._driver.get(url)

    def refresh(self) -> None:
        self._require_driver()
        self._driver.refresh()

    def back(self) -> None:
        self._require_driver()
        self._driver.back()

    def current_url(self) -> str:
        self._require_driver()
        return self._driver.current_url

    # =====================
    # find
    # =====================

    def find(self, by: By, value: str):
        self._require_driver()
        return self._driver.find_element(by, value)

    def find_all(self, by: By, value: str):
        self._require_driver()
        return self._driver.find_elements(by, value)

    def exists(self, by: By, value: str, timeout: int = 3) -> bool:
        try:
            self.wait_for(by, value, state="presence", timeout=timeout)
            return True
        except TimeoutException:
            return False

    # =====================
    # waits
    # =====================

    def wait_for(self, by: By, value: str, state: str = "presence", timeout: int = 10):
        self._require_driver()
        wait = WebDriverWait(self._driver, timeout)

        if state == "presence":
            return wait.until(EC.presence_of_element_located((by, value)))
        if state == "visible":
            return wait.until(EC.visibility_of_element_located((by, value)))
        if state == "clickable":
            return wait.until(EC.element_to_be_clickable((by, value)))
        if state == "invisible":
            return wait.until(EC.invisibility_of_element_located((by, value)))

        raise ValueError(f"Estado de espera no soportado: {state}")

    def wait_until(self, condition: Callable[[webdriver.Chrome], Any], timeout: int = 10):
        self._require_driver()
        wait = WebDriverWait(self._driver, timeout)
        return wait.until(condition)

    def wait_for_url_contains(self, text: str, timeout: int = 10) -> bool:
        self._require_driver()
        wait = WebDriverWait(self._driver, timeout)
        return wait.until(EC.url_contains(text))

    def wait_for_text(self, by: By, value: str, text: str, timeout: int = 10) -> bool:
        self._require_driver()
        wait = WebDriverWait(self._driver, timeout)
        return wait.until(EC.text_to_be_present_in_element((by, value), text))

    # =====================
    # interactions
    # =====================

    def click(self, by: By | None = None, value: str | None = None, element=None, js: bool = False, timeout: int = 10):
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para click().")
            element = self.wait_for(by, value, state="clickable", timeout=timeout)

        if js:
            self.run_js("arguments[0].click();", element)
        else:
            element.click()

    def type(self, text: str, by: By | None = None, value: str | None = None, element=None, clear: bool = False):
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para type().")
            element = self.find(by, value)

        if clear:
            element.clear()

        element.send_keys(text)

    # =====================
    # keyboard
    # =====================

    def press(self, *keys):
        self._require_driver()
        actions = ActionChains(self._driver)
        for key in keys:
            actions.key_down(key)
        for key in reversed(keys):
            actions.key_up(key)
        actions.perform()

    # =====================
    # read
    # =====================

    def get_text(self, by: By | None = None, value: str | None = None, element=None) -> str:
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para get_text().")
            element = self.find(by, value)

        return element.text

    def get_attribute(self, name: str, by: By | None = None, value: str | None = None, element=None):
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para get_attribute().")
            element = self.find(by, value)

        return element.get_attribute(name)

    # =====================
    # js
    # =====================

    def run_js(self, script: str, *args):
        self._require_driver()
        return self._driver.execute_script(script, *args)

    def scroll_into_view(self, element) -> None:
        self.run_js("arguments[0].scrollIntoView({block: 'center'});", element)

    def focus(self, element) -> None:
        self.run_js("arguments[0].focus();", element)

    # =====================
    # cookies
    # =====================

    def get_cookies(self):
        self._require_driver()
        return self._driver.get_cookies()

    def add_cookie(self, cookie_dict: dict):
        self._require_driver()
        self._driver.add_cookie(cookie_dict)

    # =====================
    # frames
    # =====================

    def switch_to_frame(self, by: By | None = None, value: str | None = None, element=None, timeout: int = 10):
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para switch_to_frame().")
            element = self.wait_for(by, value, state="presence", timeout=timeout)

        self._driver.switch_to.frame(element)

    def switch_to_default(self) -> None:
        self._require_driver()
        self._driver.switch_to.default_content()

    def switch_to_parent(self) -> None:
        self._require_driver()
        self._driver.switch_to.parent_frame()

    # =====================
    # alerts
    # =====================

    def wait_for_alert(self, timeout: int = 10):
        self._require_driver()
        wait = WebDriverWait(self._driver, timeout)
        return wait.until(EC.alert_is_present())

    def accept_alert(self, timeout: int = 10) -> str:
        alert = self.wait_for_alert(timeout)
        text = alert.text
        alert.accept()
        return text

    def dismiss_alert(self, timeout: int = 10) -> str:
        alert = self.wait_for_alert(timeout)
        text = alert.text
        alert.dismiss()
        return text

    def get_alert_text(self, timeout: int = 10) -> str:
        alert = self.wait_for_alert(timeout)
        return alert.text

    # =====================
    # downloads
    # =====================

    def wait_for_download(
        self,
        filename_contains: str | None = None,
        timeout: int = 30,
        poll_interval: float = 0.5,
    ) -> str:
        """
        Espera a que termine una descarga en download_dir.
        Si filename_contains se especifica, filtra por nombre.
        Devuelve la ruta del archivo descargado.
        """
        self._require_driver()

        if not self.download_dir:
            raise ValueError("No se configuró download_dir en BrowserTools.")

        import time
        from pathlib import Path

        download_path = Path(self.download_dir)
        end_time = time.time() + timeout

        while time.time() < end_time:
            files = list(download_path.glob("*"))

            # Excluir archivos temporales de Chrome
            completed_files = [
                f for f in files
                if not f.name.endswith(".crdownload")
            ]

            if filename_contains:
                completed_files = [
                    f for f in completed_files
                    if filename_contains in f.name
                ]

            if completed_files:
                # devolver el más reciente
                latest = max(completed_files, key=lambda f: f.stat().st_mtime)
                return str(latest)

            time.sleep(poll_interval)

        raise TimeoutException("Tiempo de espera agotado esperando descarga.")
    
    # =====================
    # utils
    # =====================

    def screenshot(self, path: str) -> None:
        self._require_driver()
        self._driver.save_screenshot(path)

    def is_active(self) -> bool:
        return self._driver is not None

    # =====================
    # internal
    # =====================

    def _require_driver(self):
        if self._driver is None:
            raise RuntimeError("El driver no ha sido iniciado. Llame a start() primero.")

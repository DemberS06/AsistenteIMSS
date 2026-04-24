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


# Mapeo de strings legibles a By de Selenium
# Los services usan estos strings en lugar de importar By directamente
_BY_MAP = {
    "id":       By.ID,
    "css":      By.CSS_SELECTOR,
    "xpath":    By.XPATH,
    "name":     By.NAME,
    "tag":      By.TAG_NAME,
    "class":    By.CLASS_NAME,
    "link":     By.LINK_TEXT,
    "partial":  By.PARTIAL_LINK_TEXT,
}


def _resolve_by(by: str | By) -> By:
    if isinstance(by, str) and by in _BY_MAP:
        return _BY_MAP[by]
    return by  # ya es un By o un string de By directo


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
                "plugins.always_open_pdf_externally": True,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.default_content_settings.popups": 0,
            }
            options.add_experimental_option("prefs", prefs)

        for opt in self.extra_options:
            options.add_argument(opt)

        self._driver = webdriver.Chrome(options=options)

    def close(self) -> None:
        if self._driver:
            self._driver.quit()
            self._driver = None

    @property
    def driver(self) -> webdriver.Chrome | None:
        """Expone el driver para casos que lo necesiten."""
        return self._driver

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

    def find(self, by: str | By, value: str):
        self._require_driver()
        return self._driver.find_element(_resolve_by(by), value)

    def find_all(self, by: str | By, value: str) -> list:
        self._require_driver()
        return self._driver.find_elements(_resolve_by(by), value)

    def find_first(self, selectors: list[str]) -> object | None:
        """Primer elemento encontrado de la lista de selectores CSS."""
        self._require_driver()
        for sel in selectors:
            try:
                els = self._driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    return els[0]
            except Exception:
                continue
        return None

    def find_all_css(self, selector: str) -> list:
        """Busca todos los elementos por selector CSS."""
        self._require_driver()
        return self._driver.find_elements(By.CSS_SELECTOR, selector)

    def find_all_xpath(self, xpath: str) -> list:
        """Busca todos los elementos por XPath."""
        self._require_driver()
        return self._driver.find_elements(By.XPATH, xpath)

    def find_first_xpath(self, xpath: str) -> object | None:
        """Primer elemento encontrado por XPath."""
        self._require_driver()
        try:
            els = self._driver.find_elements(By.XPATH, xpath)
            return els[0] if els else None
        except Exception:
            return None

    def click_first(self, selectors: list[str]) -> bool:
        """Clic en el primer elemento encontrado de la lista. Devuelve True si lo encontró."""
        el = self.find_first(selectors)
        if el is None:
            return False
        try:
            el.click()
            return True
        except Exception:
            try:
                self._driver.execute_script("arguments[0].click();", el)
                return True
            except Exception:
                return False

    def exists(self, by: str | By, value: str, timeout: int = 3) -> bool:
        try:
            self.wait_for(by, value, state="presence", timeout=timeout)
            return True
        except TimeoutException:
            return False

    # =====================
    # waits
    # =====================

    def wait_for(self, by: str | By, value: str, state: str = "presence", timeout: int = 10):
        self._require_driver()
        resolved = _resolve_by(by)
        wait = WebDriverWait(self._driver, timeout)

        if state == "presence":
            return wait.until(EC.presence_of_element_located((resolved, value)))
        if state == "visible":
            return wait.until(EC.visibility_of_element_located((resolved, value)))
        if state == "clickable":
            return wait.until(EC.element_to_be_clickable((resolved, value)))
        if state == "invisible":
            return wait.until(EC.invisibility_of_element_located((resolved, value)))

        raise ValueError(f"Estado de espera no soportado: {state}")

    def wait_until(self, condition: Callable[[webdriver.Chrome], Any], timeout: int = 10):
        self._require_driver()
        return WebDriverWait(self._driver, timeout).until(condition)

    def wait_for_url_contains(self, text: str, timeout: int = 10) -> bool:
        self._require_driver()
        return WebDriverWait(self._driver, timeout).until(EC.url_contains(text))

    def wait_for_text(self, by: str | By, value: str, text: str, timeout: int = 10) -> bool:
        self._require_driver()
        resolved = _resolve_by(by)
        return WebDriverWait(self._driver, timeout).until(
            EC.text_to_be_present_in_element((resolved, value), text)
        )

    # =====================
    # interactions
    # =====================

    def click(self, by: str | By | None = None, value: str | None = None, element=None, js: bool = False, timeout: int = 10):
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para click().")
            element = self.wait_for(by, value, state="clickable", timeout=timeout)

        if js:
            self.run_js("arguments[0].click();", element)
        else:
            element.click()

    def action_click(self, element) -> None:
        """Clic con ActionChains — mantiene el foco en el navegador."""
        self._require_driver()
        ActionChains(self._driver).move_to_element(element).click().perform()

    def type(self, text: str, by: str | By | None = None, value: str | None = None, element=None, clear: bool = False):
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para type().")
            element = self.find(by, value)

        if clear:
            element.clear()

        element.send_keys(text)

    def clear_and_type(self, element, text: str) -> None:
        """Limpia el campo y escribe el texto."""
        try:
            element.clear()
        except Exception:
            pass
        element.send_keys(text)

    # =====================
    # keyboard
    # =====================

    def press(self, *keys) -> None:
        """Envía teclas dentro del navegador con ActionChains."""
        self._require_driver()
        actions = ActionChains(self._driver)
        for key in keys:
            actions.key_down(key)
        for key in reversed(keys):
            actions.key_up(key)
        actions.perform()

    def press_enter(self) -> None:
        """Envía Enter dentro del navegador."""
        from selenium.webdriver.common.keys import Keys
        self.press(Keys.ENTER)

    def press_system_key(self, key: str) -> None:
        """Envía una tecla a nivel del sistema operativo (para ventanas nativas)."""
        import pyautogui
        pyautogui.press(key)

    def send_keys_to(self, element, *keys) -> None:
        """Envía teclas directamente a un elemento."""
        element.send_keys(*keys)

    # =====================
    # read
    # =====================

    def get_text(self, by: str | By | None = None, value: str | None = None, element=None) -> str:
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para get_text().")
            element = self.find(by, value)

        return element.text

    def get_attribute(self, name: str, by: str | By | None = None, value: str | None = None, element=None):
        self._require_driver()

        if element is None:
            if by is None or value is None:
                raise ValueError("Debe proporcionar element o by/value para get_attribute().")
            element = self.find(by, value)

        return element.get_attribute(name)

    def get_element_attribute(self, element, name: str) -> str:
        """Obtiene un atributo de un elemento ya encontrado."""
        try:
            return element.get_attribute(name) or ""
        except Exception:
            return ""

    def is_displayed(self, element) -> bool:
        """Devuelve True si el elemento está visible en pantalla."""
        try:
            return element.is_displayed()
        except Exception:
            return False

    def get_size(self, element) -> dict:
        """Devuelve el tamaño del elemento como dict {width, height}."""
        try:
            return element.size or {}
        except Exception:
            return {}

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

    def focus_and_scroll(self, element) -> None:
        """Hace scroll al elemento y le da foco en un solo paso."""
        self.run_js(
            "arguments[0].scrollIntoView(true); arguments[0].focus();", element
        )

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

    def switch_to_frame(self, by: str | By | None = None, value: str | None = None, element=None, timeout: int = 10):
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
        return WebDriverWait(self._driver, timeout).until(EC.alert_is_present())

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
        return self.wait_for_alert(timeout).text

    # =====================
    # downloads
    # =====================

    def wait_for_download(
        self,
        filename_contains: str | None = None,
        timeout: int = 30,
        poll_interval: float = 0.5,
    ) -> str:
        self._require_driver()

        if not self.download_dir:
            raise ValueError("No se configuró download_dir en BrowserTools.")

        import time
        from pathlib import Path

        download_path = Path(self.download_dir)
        end_time = time.time() + timeout

        while time.time() < end_time:
            files = list(download_path.glob("*"))
            completed_files = [f for f in files if not f.name.endswith(".crdownload")]

            if filename_contains:
                completed_files = [f for f in completed_files if filename_contains in f.name]

            if completed_files:
                return str(max(completed_files, key=lambda f: f.stat().st_mtime))

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

    def same_element(self, el1, el2) -> bool:
        """Devuelve True si dos elementos del DOM son el mismo nodo."""
        try:
            return self.run_js("return arguments[0] === arguments[1];", el1, el2)
        except Exception:
            return False

    # =====================
    # internal
    # =====================

    def _require_driver(self):
        if self._driver is None:
            raise RuntimeError("El driver no ha sido iniciado. Llame a start() primero.")
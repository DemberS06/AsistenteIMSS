# service/whatsapp_web.py
from __future__ import annotations
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

from tools.browser import BrowserTools


class WhatsAppService:

    URL = "https://web.whatsapp.com/"

    def __init__(
        self,
        browser: BrowserTools = BrowserTools(),
        qr_screenshot_path: str = "whatsapp_qr.png",
        default_timeout: int = 10,
    ):
        self.browser = browser
        self.qr_screenshot_path = qr_screenshot_path
        self.default_timeout = default_timeout
        self._chat_open = False

    # =========================================================
    # SESSION
    # =========================================================

    def start_session(self) -> None:

        if not self.browser.is_active():
            self.browser.start()

        self.browser.go_to(self.URL)

        if self._is_logged_in(timeout=5):
            return

        self.browser.screenshot(self.qr_screenshot_path)
        raise TimeoutException(
            f"No active session. Scan QR at: {self.qr_screenshot_path}"
        )

    def close_session(self, logout: bool = False) -> None:

        if logout and self._is_logged_in():
            self.browser.click(By.CSS_SELECTOR, "span[data-testid='menu']")
            self.browser.click(
                By.XPATH,
                "//div[@role='button'][.//span[text()='Cerrar sesión']]"
            )

        self.browser.close()
        self._chat_open = False

    # =========================================================
    # CHAT
    # =========================================================

    def open_chat(self, phone_number: str) -> None:

        if not self._is_logged_in():
            raise TimeoutException("WhatsApp session not active.")

        phone = str(phone_number).strip()

        self.browser.go_to(
            f"https://web.whatsapp.com/send?phone={phone}"
        )

        self.browser.wait_for(
            By.CSS_SELECTOR,
            "div[data-testid='conversation-panel']",
            timeout=self.default_timeout,
        )

        self._chat_open = True

    # =========================================================
    # MESSAGE
    # =========================================================

    def send_message(self, message: str) -> None:

        if not self._chat_open:
            raise RuntimeError("No chat is currently open.")

        input_box = self.browser.wait_for(
            By.CSS_SELECTOR,
            "div[contenteditable='true'][data-tab='10']",
            state="visible",
            timeout=self.default_timeout,
        )

        lines = message.splitlines()

        for i, line in enumerate(lines):
            input_box.send_keys(line)
            if i < len(lines) - 1:
                input_box.send_keys(Keys.SHIFT, Keys.ENTER)

        input_box.send_keys(Keys.ENTER)

    # =========================================================
    # PDF
    # =========================================================

    def send_pdf(
        self,
        pdf_path: str,
        message: Optional[str] = None,
    ) -> None:

        if not self._chat_open:
            raise RuntimeError("No chat is currently open.")

        if message:
            self.send_message(message)

        self.browser.click(
            By.CSS_SELECTOR,
            "span[data-testid='clip']",
            timeout=self.default_timeout,
        )

        file_input = self.browser.wait_for(
            By.CSS_SELECTOR,
            "input[type='file']",
            state="presence",
            timeout=self.default_timeout,
        )

        file_input.send_keys(pdf_path)

        self.browser.click(
            By.CSS_SELECTOR,
            "span[data-icon='send']",
            timeout=self.default_timeout,
        )

    # =========================================================
    # PRIVATE
    # =========================================================

    def _is_logged_in(self, timeout: int = 5) -> bool:
        try:
            self.browser.wait_for(
                By.CSS_SELECTOR,
                "div[data-testid='pane-side']",
                timeout=timeout,
            )
            return True
        except TimeoutException:
            return False
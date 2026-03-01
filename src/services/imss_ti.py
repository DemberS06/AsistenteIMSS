# services/imss_ti.py
from __future__ import annotations
from typing import Dict
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from tools.browser import BrowserTools
from tools.file import move_file
from config import IMSS_TI_URL


class IMSSTiService:

    def __init__(
        self,
        base_url: str = IMSS_TI_URL,
        default_timeout: int = 10,
        browser: BrowserTools = BrowserTools(),
    ):
        self.browser = browser
        self.base_url = base_url
        self.default_timeout = default_timeout

    # =========================
    # SESSION
    # =========================

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

    # =========================
    # PAGE
    # =========================

    def open_page(self) -> None:
        try:
            self.browser.go_to(self.base_url)
            self.browser.wait_for(By.TAG_NAME, "body", timeout=self.default_timeout)
        except Exception as e:
            raise RuntimeError(f"[open_page] {e}")

    # =========================
    # CAPTCHA
    # =========================

    def get_captcha_image(self, element_id: str = "captchaImg") -> bytes:
        try:
            element = self.browser.wait_for(
                By.ID,
                element_id,
                state="visible",
                timeout=self.default_timeout,
            )

            if element.size["width"] == 0:
                raise RuntimeError("Captcha rendered with zero size.")

            return element.screenshot_as_png

        except Exception as e:
            raise RuntimeError(f"[get_captcha_image] {e}")

    # =========================
    # FORM
    # =========================

    def fill_form(self, fields: Dict[str, str]) -> None:
        try:
            if not isinstance(fields, dict):
                raise RuntimeError("Fields must be a dictionary.")

            for field_id, value in fields.items():
                self.browser.type(
                    value,
                    by=By.ID,
                    value=field_id,
                    clear=True,
                )
        except Exception as e:
            raise RuntimeError(f"[fill_form] {e}")

    def submit_form(self) -> None:
        try:
            self.browser.click(By.ID, "continuar")
        except Exception as e:
            raise RuntimeError(f"[submit_form] {e}")

    def validate_field_errors(self) -> Dict[str, str]:
        try:
            error_ids = ["errorCurp", "errorRfc", "errorNss", "errorEmail"]
            errors = {}

            for eid in error_ids:
                if self.browser.exists(By.ID, eid, timeout=1):
                    text = self.browser.get_text(By.ID, eid).strip()
                    if text:
                        errors[eid] = text

            return errors

        except Exception as e:
            raise RuntimeError(f"[validate_field_errors] {e}")

    def process_form(self, fields: Dict[str, str]) -> None:
        try:
            required = ["curp", "nss", "email", "emailConfirmacion", "captcha"]

            for field in required:
                if not fields.get(field, "").strip():
                    raise RuntimeError(f"Field '{field}' is required.")

            self.fill_form(fields)
            self.submit_form()

            errors = self.validate_field_errors()
            if errors:
                first_msg = next(iter(errors.values()))
                raise RuntimeError(first_msg)

        except Exception as e:
            raise RuntimeError(f"[process_form] {e}")

    # =========================
    # REGISTRATION
    # =========================

    def complete_registration(self) -> None:
        try:
            sequence = [
                "submitContinuar",
                "continuar",
                "checkRenovacionAut",
                "terminos",
                "continuar",
                "guarda",
            ]

            for btn_id in sequence:
                if not self.browser.exists(By.ID, btn_id, timeout=2):
                    raise RuntimeError(
                        f"Expected button '{btn_id}' not found."
                    )

                self.browser.click(By.ID, btn_id)

        except Exception as e:
            raise RuntimeError(f"[complete_registration] {e}")

    def register(self, fields: Dict[str, str]) -> None:
        try:
            self.process_form(fields)

            if self.browser.exists(By.ID, "mensajeYaRegistrado", timeout=2):
                raise RuntimeError("Worker already registered.")

            self.complete_registration()

        except Exception as e:
            raise RuntimeError(f"[register] {e}")

    # =========================
    # PDF DOWNLOAD
    # =========================

    def download_pdfs(
        self,
        click_selector: str = "span.glyphicon.glyphicon-file",
        click_count: int = 2,
    ) -> str:
        try:
            icons = self.browser.find_all(By.CSS_SELECTOR, click_selector)

            if not icons:
                raise RuntimeError("No PDF icons found.")

            for i in range(min(click_count, len(icons))):
                icons[i].click()

            file_path = self.browser.wait_for_download(timeout=30)

            return file_path

        except Exception as e:
            raise RuntimeError(f"[download_pdfs] {e}")

    def register_and_download(
        self,
        fields: Dict[str, str],
        target_folder: str,
    ) -> str:
        try:
            if not target_folder:
                raise RuntimeError("Download folder not defined.")

            self.register(fields)

            temp_path = self.download_pdfs()

            final_path = move_file(temp_path, target_folder)

            return final_path

        except Exception as e:
            raise RuntimeError(f"[register_and_download] {e}")

    def get_pdf_only(self, fields: Dict[str, str]) -> str:
        try:
            self.process_form(fields)
            return self.download_pdfs()
        except Exception as e:
            raise RuntimeError(f"[get_pdf_only] {e}")
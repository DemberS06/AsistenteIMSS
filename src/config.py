# config.py
import os


def _user_data_dir():
    base = os.getenv("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    appdir = os.path.join(base, "AsistenteIMSS")
    try:
        os.makedirs(appdir, exist_ok=True)
    except Exception:
        pass
    return appdir


DATA_DIR    = _user_data_dir()
IMSS_TI_URL = "https://adodigital.imss.gob.mx/pti/inicio"
WA_URL      = "https://web.whatsapp.com/"

WA_SELECTORS = {
    "search_inputs": [
        "input[aria-label='Search or start a new chat']",
        "input[aria-label='Buscar o iniciar un chat']",
        "input[role='textbox'][data-tab='3']",
        "input[placeholder='Search or start a new chat']",
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
}
import os

def _user_data_dir():
    base = os.getenv("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    appdir = os.path.join(base, "AsistenteIMSS")
    try:
        os.makedirs(appdir, exist_ok=True)
    except Exception:
        pass
    return appdir

DATA_DIR = _user_data_dir()
IMSS_TI_URL = "https://adodigital.imss.gob.mx/pti/inicio"
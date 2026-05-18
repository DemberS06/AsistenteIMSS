# config.py
"""
Configuración central de la aplicación AsistenteIMSS.
Contiene todas las constantes, rutas, URLs, selectores y configuraciones.
"""

import os


# ══════════════════════════════════════════════════════════
# DIRECTORIOS
# ══════════════════════════════════════════════════════════

def _user_data_dir():
    base = os.getenv("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    appdir = os.path.join(base, "AsistenteIMSS")
    try:
        os.makedirs(appdir, exist_ok=True)
    except Exception:
        pass
    return appdir


DATA_DIR = _user_data_dir()
ERROR_LOG_FILE = os.path.join(DATA_DIR, "error.log")
CACHE_FILE = os.path.join(DATA_DIR, "app_cache.json")


# ══════════════════════════════════════════════════════════
# URLs
# ══════════════════════════════════════════════════════════

# IMSS - Trabajadores Independientes
IMSS_TI_URL = "https://adodigital.imss.gob.mx/pti/inicio"

# IMSS - Modalidad 40
IMSS_M40_URL = "https://serviciosdigitales.imss.gob.mx/portal-ciudadano-web-externo/home"

# WhatsApp Web
WHATSAPP_URL = "https://web.whatsapp.com/"


# ══════════════════════════════════════════════════════════
# SELECTORES - IMSS TI
# ══════════════════════════════════════════════════════════

IMSS_TI_SELECTORS = {
    # IDs de campos del formulario
    "captcha_img": "captchaImg",
    "curp_input": "curp",
    "rfc_input": "rfc",
    "nss_input": "nss",
    "email_input": "email",
    "email_confirm_input": "emailConfirmacion",
    "captcha_input": "captcha",
    
    # Botones del flujo
    "continuar_button": "continuar",
    "submit_continuar": "submitContinuar",
    "check_renovacion": "checkRenovacionAut",
    "terminos": "terminos",
    "guarda_button": "guarda",
    "salir_button": "salir",
    "submit_cancelar": "submitCancelar",
    
    # Mensajes de error
    "error_curp": "errorCurp",
    "error_rfc": "errorRfc",
    "error_nss": "errorNss",
    "error_email": "errorEmail",
    "error_form": "errorForm",
    "mensaje_ya_registrado": "mensajeYaRegistrado",
    
    # Iconos de PDF
    "pdf_icons": "span.glyphicon.glyphicon-file",
}


# ══════════════════════════════════════════════════════════
# SELECTORES - IMSS M40
# ══════════════════════════════════════════════════════════

IMSS_M40_SELECTORS = {
    # ──────────────────────────────────────────────────────
    # Primera pantalla - Buscar
    # ──────────────────────────────────────────────────────
    "captcha_img": "captchaImg",
    "curp_input": "registroCurp",
    "email_input": "correoInput",
    "email_confirm_input": "correoConfirmacionInput",
    "captcha_input": "strCaptcha",
    "buscar_button": "buscar",
    
    # ──────────────────────────────────────────────────────
    # Segunda pantalla - Submenú
    # ──────────────────────────────────────────────────────
    "tile_inscripcion": "inscripcionCVRO",  # Tile para abrir submenú
    
    # ──────────────────────────────────────────────────────
    # Tercera pantalla - Descargar PDF
    # ──────────────────────────────────────────────────────
    # El link <a> que contiene el icono y ejecuta onclick="imprimePago(...)"
    "download_pdf_link": "a.link.print",  # CSS selector del <a>
    
    # ──────────────────────────────────────────────────────
    # Cuarta pantalla - Cerrar wizard
    # ──────────────────────────────────────────────────────
    "cerrar_wizard_button": "cerrarWizard",
    
    # ──────────────────────────────────────────────────────
    # Quinta pantalla - Aceptar
    # ──────────────────────────────────────────────────────
    # No tiene ID, buscar por texto "Aceptar"
    "aceptar_button_text": "Aceptar",
    
    # ──────────────────────────────────────────────────────
    # Salir (disponible en cualquier momento)
    # ──────────────────────────────────────────────────────
    "salir_link": "cerrarSesionLink",
    
    # ──────────────────────────────────────────────────────
    # Mensajes de error (pendientes de confirmar)
    # ──────────────────────────────────────────────────────
    "error_curp": None,        # TODO: Confirmar selector
    "error_email": None,       # TODO: Confirmar selector
    "error_form": None,        # TODO: Confirmar selector
    "mensaje_ya_registrado": None,  # TODO: Confirmar selector
}


# ══════════════════════════════════════════════════════════
# SELECTORES - WHATSAPP WEB
# ══════════════════════════════════════════════════════════

WHATSAPP_SELECTORS = {
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


# ══════════════════════════════════════════════════════════
# TIMEOUTS Y DELAYS
# ══════════════════════════════════════════════════════════

# Timeouts en segundos
TIMEOUTS = {
    "default": 10,
    "long": 60,
    "short": 5,
    "element_check": 1,
    "button_sequence": 2,
    "whatsapp_login": 30,
    "whatsapp_url": 8,
    "whatsapp_chat_open": 5,
    "search_field": 4,
    "search_results": 3,
    "file_input": 6,
    "download": 30,
}

# Delays en segundos
DELAYS = {
    "after_click": 0.5,
    "after_submit": 0.5,
    "pdf_icon_click": 0.2,
    "download_complete": 0.5,
    "download_poll": 0.25,
    "whatsapp_search": 0.6,
    "whatsapp_enter": 0.35,
    "whatsapp_clip": 0.8,
    "whatsapp_doc_click": 0.2,
    "whatsapp_file_attach": 2.0,
    "whatsapp_escape": 1.0,
    "whatsapp_send": 2.0,
    "browser_exit": 1.0,
}


# ══════════════════════════════════════════════════════════
# CAMPOS REQUERIDOS
# ══════════════════════════════════════════════════════════

IMSS_TI_REQUIRED_FIELDS = ["curp", "nss", "email", "emailConfirmacion", "captcha"]

# M40 - Primera pantalla (Buscar)
IMSS_M40_REQUIRED_FIELDS = ["curp", "email", "emailConfirmacion", "captcha"]


# ══════════════════════════════════════════════════════════
# SECUENCIAS DE REGISTRO
# ══════════════════════════════════════════════════════════

IMSS_TI_REGISTRATION_SEQUENCE = [
    "submitContinuar",
    "continuar",
    "checkRenovacionAut",
    "terminos",
    "continuar",
    "guarda",
]

# M40 - Secuencia completa
IMSS_M40_REGISTRATION_SEQUENCE = [
    # Ya no se incluye "buscar" aquí porque se ejecuta en process_form()
    "tile_inscripcion",      # Abrir submenú de inscripción
    "cerrar_wizard_button",  # Cerrar wizard después de descargar
    "aceptar_button_text",   # Aceptar (botón sin ID)
]


# ══════════════════════════════════════════════════════════
# CONFIGURACIÓN DE DESCARGAS
# ══════════════════════════════════════════════════════════

DOWNLOAD_CONFIG = {
    "temp_dir_name": "imss_ti_downloads_temp",
    "pdf_click_count": 2,
    "crdownload_extension": ".crdownload",
}


# ══════════════════════════════════════════════════════════
# CONFIGURACIÓN DE WHATSAPP
# ══════════════════════════════════════════════════════════

WHATSAPP_CONFIG = {
    "profile_dir_name": "chrome_wa_profile",
    "profile_name": "Default",
}


# ══════════════════════════════════════════════════════════
# VALIDACIONES
# ══════════════════════════════════════════════════════════

VALIDATION = {
    "curp_length": 18,
    "rfc_length_fisica": 13,
    "rfc_length_moral": 12,
    "nss_length": 11,
    "allowed_folder_chars": (' ', '-', '_'),
    "fallback_folder_name": "Sin_nombre",
}


# ══════════════════════════════════════════════════════════
# EXTENSIONES DE ARCHIVO
# ══════════════════════════════════════════════════════════

FILE_EXTENSIONS = {
    "excel": ('.xlsx', '.xls'),
    "pdf": '.pdf',
}


# ══════════════════════════════════════════════════════════
# NOMBRES DE COLUMNAS EXCEL
# ══════════════════════════════════════════════════════════

EXCEL_COLUMNS_TI = [
    "ID",
    "CLIENTE",
    "NSS",
    "CURP",
    "RFC",
    "CORREO",
    "NUMERO",
    "CARPETAPDF",
    "PDF",
    "MENSAJE",
]

# M40 - Mismas columnas que TI
EXCEL_COLUMNS_M40 = [
    "ID",
    "CLIENTE",
    "NSS",
    "CURP",
    "RFC",
    "CORREO",
    "NUMERO",
    "CARPETAPDF",
    "PDF",
    "MENSAJE",
]


# ══════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL NAVEGADOR
# ══════════════════════════════════════════════════════════

BROWSER_OPTIONS = {
    "start_maximized": True,
    "disable_notifications": True,
}

DOWNLOAD_PREFS = {
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True,
    "profile.default_content_setting_values.automatic_downloads": 1,
    "profile.default_content_settings.popups": 0,
}
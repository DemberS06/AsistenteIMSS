# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec correcto para AsistenteIMSS.

Uso desde la raíz del proyecto, con el venv activado:
    pyinstaller --clean AsistenteIMSS.spec

Genera un solo ejecutable:
    dist/AsistenteIMSS.exe
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, copy_metadata

block_cipher = None

ROOT = Path(SPECPATH).resolve()
SRC = ROOT / "src"

ICON = None
# Si tienes ícono, usa por ejemplo:
# ICON = str(ROOT / "assets" / "icons" / "app.ico")

# ==========================================================
# Hidden imports
# ==========================================================
hiddenimports = []

# Paquetes propios. OJO: NO usar "src.config" porque tu código importa "config".
hiddenimports += [
    "config",
    "launcher",

    "interfaz",
    "interfaz.ti",
    "interfaz.m40",

    "work_flow",
    "work_flow.imss_ti",
    "work_flow.imss_m40",

    "services",
    "services.cache",
    "services.imss_ti",
    "services.imss_m40",
    "services.imss_af",
    "services.whatsapp_web",

    "tools",
    "tools.browser",
    "tools.excel",
    "tools.file",
    "tools.pdf",

    "models",
    "models.mensaje",
    "models.trabajador",
    "models.trabajador_ti",
    "models.trabajador_m40",
]

# PyQt5
hiddenimports += [
    "PyQt5",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.sip",
]

# Librerías principales
hiddenimports += [
    "pandas",
    "numpy",
    "openpyxl",
    "openpyxl.cell._writer",
    "PyPDF2",
    "selenium",
    "selenium.webdriver",
    "selenium.webdriver.chrome.webdriver",
    "selenium.webdriver.chrome.options",
    "selenium.webdriver.common.by",
    "selenium.webdriver.common.keys",
    "selenium.webdriver.common.action_chains",
    "selenium.webdriver.support.ui",
    "selenium.webdriver.support.expected_conditions",
]

# CRÍTICO: pyautogui y dependencias indirectas.
# Si tools/browser.py importa pyautogui, PyInstaller puede no detectarlo bien.
hiddenimports += [
    "pyautogui",
    "pyscreeze",
    "pygetwindow",
    "pymsgbox",
    "pytweening",
    "mouseinfo",
    "pyperclip",
    "pyrect",
    "PIL",
    "PIL.Image",
    "PIL.ImageGrab",
    "PIL.ImageOps",
    "PIL.ImageChops",
]

# Recolectar submódulos de paquetes conflictivos.
for pkg in (
    "interfaz",
    "work_flow",
    "services",
    "tools",
    "models",
    "pandas",
    "numpy",
    "openpyxl",
    "selenium",
    "PyPDF2",
    "pyautogui",
    "pyscreeze",
    "pygetwindow",
    "pymsgbox",
    "pytweening",
    "mouseinfo",
    "pyperclip",
    "PIL",
):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

# ==========================================================
# Datas / binaries
# ==========================================================
datas = []
binaries = []

# collect_all ayuda especialmente con pyautogui/PIL y paquetes con metadata.
for pkg in (
    "pandas",
    "numpy",
    "openpyxl",
    "selenium",
    "PyPDF2",
    "pyautogui",
    "pyscreeze",
    "pygetwindow",
    "pymsgbox",
    "pytweening",
    "mouseinfo",
    "pyperclip",
    "PIL",
):
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hiddenimports
    except Exception:
        try:
            datas += collect_data_files(pkg)
        except Exception:
            pass
        try:
            datas += copy_metadata(pkg)
        except Exception:
            pass

# Si luego agregas assets reales, descomenta:
# ASSETS = ROOT / "assets"
# if ASSETS.exists():
#     datas.append((str(ASSETS), "assets"))

# No metas Data/ de pruebas al ejecutable.

excludes = [
    "__pycache__",
    "tkinter",
    "unittest",
    "pytest",
    "IPython",
    "notebook",
]

# ==========================================================
# Build onefile
# ==========================================================
a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AsistenteIMSS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
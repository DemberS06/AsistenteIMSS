# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
import os

block_cipher = None

datas = []
binaries = []
hiddenimports = []

# ============================================================
# ASSETS
# ============================================================

if os.path.exists('assets'):
    datas.append(('assets', 'assets'))

if os.path.exists('Data'):
    datas.append(('Data', 'Data'))

# ============================================================
# SELENIUM
# ============================================================

tmp = collect_all('selenium')
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

# ============================================================
# OPENPYXL
# ============================================================

tmp = collect_all('openpyxl')
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

# ============================================================
# WEBDRIVER MANAGER
# ============================================================

tmp = collect_all('webdriver_manager')
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

# ============================================================
# PYPDF2
# ============================================================

tmp = collect_all('PyPDF2')
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

# ============================================================
# PYAUTOGUI
# ============================================================

tmp = collect_all('pyautogui')
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

hiddenimports += [
    'mouseinfo',
    'pygetwindow',
    'pymsgbox',
    'pyscreeze',
]

# ============================================================
# MÓDULOS INTERNOS
# ============================================================

hiddenimports += [
    'src.config',
    'src.launcher',
    'src.main',

    'src.tools',
    'src.tools.browser',
    'src.tools.excel',
    'src.tools.file',
    'src.tools.pdf',

    'src.services',
    'src.services.imss_ti',
    'src.services.imss_m40',
    'src.services.imss_af',
    'src.services.whatsapp_web',
    'src.services.cache',

    'src.models',
    'src.models.trabajador',
    'src.models.trabajador_ti',
    'src.models.trabajador_m40',
    'src.models.mensaje',

    'src.interfaz',
    'src.interfaz.ti',
    'src.interfaz.m40',

    'src.work_flow',
    'src.work_flow.imss_ti',
    'src.work_flow.imss_m40',
]

# ============================================================
# ANALYSIS
# ============================================================

a = Analysis(
    ['src\\launcher.py'],
    pathex=['src', '.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    excludes=[
        'pytest',
        '_pytest',
        'tests',
        'test',

        'pandas.tests',
        'numpy.tests',

        'matplotlib',
        'tkinter',
    ],

    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],

    name='AsistenteIMSS',

    debug=False,

    bootloader_ignore_signals=False,
    strip=False,

    upx=True,
    upx_exclude=[],

    runtime_tmpdir=None,

    console=True,

    disable_windowed_traceback=False,

    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,

    icon='assets\\app.ico' if os.path.exists('assets\\app.ico') else None,
)
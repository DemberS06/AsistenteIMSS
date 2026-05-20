# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_all
import os

block_cipher = None

# Datos y binarios
datas = []
binaries = []
hiddenimports = []

# Agregar carpetas de assets y Data
if os.path.exists('assets'):
    datas.append(('assets', 'assets'))
if os.path.exists('Data'):
    datas.append(('Data', 'Data'))

# ============================================================
# DEPENDENCIAS EXTERNAS - Todas las librerías third-party
# ============================================================

# Selenium completo
hiddenimports += collect_submodules('selenium')

# Pandas y dependencias
hiddenimports += collect_submodules('pandas')

# NumPy
hiddenimports += collect_submodules('numpy')

# Excel - openpyxl
hiddenimports += collect_submodules('openpyxl')

# PDF - PyPDF2 (CRÍTICO)
hiddenimports.append('PyPDF2')
hiddenimports.append('PyPDF2.generic')
hiddenimports.append('PyPDF2._reader')
hiddenimports.append('PyPDF2._writer')
hiddenimports.append('PyPDF2._page')
hiddenimports.append('PyPDF2._utils')
hiddenimports.append('PyPDF2.errors')

# Recolectar TODO de PyPDF2
tmp_ret = collect_all('PyPDF2')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# PyQt5 - Recolectar todo
tmp_ret = collect_all('PyQt5')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# webdriver_manager
tmp_ret = collect_all('webdriver_manager')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# ============================================================
# MÓDULOS INTERNOS DEL PROYECTO
# ============================================================

hiddenimports += [
    # Config y launcher
    'src.config',
    'src.launcher',
    'src.main',
    
    # Tools
    'src.tools',
    'src.tools.browser',
    'src.tools.excel',
    'src.tools.file',
    'src.tools.pdf',
    
    # Services
    'src.services',
    'src.services.imss_ti',
    'src.services.imss_m40',
    'src.services.imss_af',
    'src.services.whatsapp_web',
    'src.services.cache',
    
    # Models
    'src.models',
    'src.models.trabajador',
    'src.models.trabajador_ti',
    'src.models.trabajador_m40',
    'src.models.mensaje',
    
    # Interfaz (TI y M40)
    'src.interfaz',
    'src.interfaz.ti',
    'src.interfaz.m40',
    
    # Workflow
    'src.work_flow',
    'src.work_flow.imss_ti',
    'src.work_flow.imss_m40',
]

# ============================================================
# MÓDULOS ESTÁNDAR DE PYTHON necesarios explícitamente
# ============================================================

hiddenimports += [
    'dataclasses',
    'pathlib',
    'datetime',
    'tempfile',
    'shutil',
    'traceback',
    'unicodedata',
    're',
    'os',
    'sys',
    'time',
    'json',
    'logging',
]

# ============================================================
# ANÁLISIS
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
        'matplotlib',
        'tkinter',
        'PIL',
        'pytest',
        'test',
        'tests',
        '_pytest',
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
    console=False,  # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\app.ico' if os.path.exists('assets\\app.ico') else None,
)

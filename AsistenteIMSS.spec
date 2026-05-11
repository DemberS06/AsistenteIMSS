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

# PDF - PyPDF2 (CRÍTICO - usado en tools/pdf.py)
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

# python-docx si existe
try:
    tmp_ret = collect_all('docx')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except:
    pass

# PyMuPDF (fitz) si existe
try:
    tmp_ret = collect_all('fitz')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except:
    pass

# ============================================================
# MÓDULOS INTERNOS DEL PROYECTO
# ============================================================

hiddenimports += [
    # Config
    'src.config',
    
    # Tools
    'src.tools',
    'src.tools.browser',
    'src.tools.excel',
    'src.tools.file',
    'src.tools.pdf',
    
    # Services
    'src.services',
    'src.services.imss_ti',
    'src.services.whatsapp_web',
    'src.services.imss_af',
    'src.services.imss_m40',
    'src.services.cache',
    
    # Models
    'src.models',
    'src.models.trabajador',
    'src.models.mensaje',
    
    # Workflow (renombrado temporalmente a _workflow)
    'src._workflow',
    'src._workflow.imss_ti',
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
]

# ============================================================
# ANÁLISIS
# ============================================================

a = Analysis(
    ['src\\interfaz.py'],
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
        'workflow.workflows',  # Excluir paquete workflow externo
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
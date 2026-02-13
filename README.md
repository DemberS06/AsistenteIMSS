# Asistente IMSS

Aplicación de escritorio (PyQt5) para agilizar el registro en el portal del IMSS, descargar comprobantes PDF, organizarlos por cliente y enviar mensaje + PDF por WhatsApp Web.
---

## Requisitos

- Windows 10/11 (64-bit)
- **Google Chrome** instalado
- Conexión a Internet solo la **primera** vez (descarga automática de ChromeDriver)

> Los datos de usuario (sesión de WhatsApp, descargas temporales y logs) se guardan en:  
> `%LOCALAPPDATA%\AsistenteIMSS`

---

## Instalación (usuario final)

1. Ejecuta `AsistenteIMSS-Setup.exe`.
2. Siguiente → Siguiente (instala por **usuario**, no pide admin).
3. Abre **Asistente IMSS** desde el menú Inicio o el acceso directo del Escritorio.

**Desinstalar:** Panel de control → Aplicaciones → “Asistente IMSS”.

---

## Uso rápido

1. En la app, pulsa **Abrir WhatsApp Web** y escanea el **QR** (solo la primera vez).
2. Pulsa **Abrir Excel** y carga tu archivo con clientes.
3. (Opcional) **Seleccionar PDF global** para autocompletar mensajes.
4. **Seleccionar carpeta final de descargas** (donde quedarán los PDFs por cliente).
5. Para un cliente: registrar/descargar PDF → revisar mensaje → **Enviar mensaje**.
6. Para varios clientes: llena **Desde / Hasta** → **Enviar rango** (sin pop-ups que bloqueen).

---

## Estructura del proyecto

~~~
tu-proyecto/
├─ interfaz.py
├─ modules/
│  ├─ __init__.py            # puede estar vacío
│  ├─ web_management.py
│  ├─ whatsapp_manager.py
│  ├─ excel_tools.py
│  └─ pdf_tools.py
├─ assets/
│  ├─ app.ico                # icono del programa (.exe)
│  └─ app_setup.ico          # (opcional) icono del instalador (Setup.exe)
├─ installer/
│  └─ AsistenteIMSS.iss      # script de Inno Setup
├─ requirements.txt
└─ README.md
~~~

---

## Desarrollo

### Crear entorno e instalar dependencias
~~~
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
~~~

### Ejecutar la app
~~~
python interfaz.py
~~~

---

## requirements.txt (recomendado)

~~~
# GUI
PyQt5==5.15.11

# Excel / Datos
pandas==2.2.2
openpyxl==3.1.5
numpy==2.0.2

# Navegación web / WhatsApp Web
selenium==4.23.1
webdriver-manager==4.0.2

# Word / PDF
python-docx==1.1.2
pypdf==4.3.1
PyMuPDF==1.24.10   # opcional; si da problema, bórralo
~~~

---

## Construir el ejecutable (.exe) con PyInstaller

> Esto genera `dist\AsistenteIMSS.exe` (portable; ya funciona sin instalar).  
> Compila con icono si tienes `assets\app.ico`.

~~~
pip install pyinstaller

pyinstaller interfaz.py --name AsistenteIMSS --onefile --windowed ^
  --icon assets\app.ico ^
  --collect-all PyQt5 ^
  --collect-submodules selenium ^
  --collect-submodules pandas ^
  --collect-submodules numpy ^
  --collect-all webdriver_manager
~~~

**Flags clave**
- `--onefile`: un solo `.exe`.
- `--windowed`: sin consola negra (GUI).
- `--icon`: icono del programa.
- `--collect-*`: asegura dependencias dinámicas (Qt, selenium, pandas, numpy, webdriver_manager).

Salida: `dist\AsistenteIMSS.exe`.

---

## Crear instalador (Setup.exe) con Inno Setup

1) Instala **Inno Setup**.  
2) Crea el archivo `installer\AsistenteIMSS.iss` con este contenido (instalación **por usuario**, sin admin):

~~~
; ===== Asistente IMSS - Instalador (Per-user, sin admin) =====
[Setup]
AppId={{8A23B90A-7F44-4C20-8F6E-4A3AD32B7A11}}
AppName=Asistente IMSS
AppVersion=1.0.0
AppPublisher=Tu Organización
DefaultDirName={userappdata}\Asistente IMSS
DefaultGroupName=Asistente IMSS
OutputDir=installer\Output
OutputBaseFilename=AsistenteIMSS-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
SetupIconFile=..\assets\app_setup.ico
UninstallDisplayIcon={app}\AsistenteIMSS.exe

[Files]
Source: "dist\AsistenteIMSS.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{localappdata}\AsistenteIMSS"

[Icons]
Name: "{group}\Asistente IMSS"; Filename: "{app}\AsistenteIMSS.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\Asistente IMSS"; Filename: "{app}\AsistenteIMSS.exe"; Tasks: desktopicon; WorkingDir: "{app}"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; Flags: unchecked

[Run]
Filename: "{app}\AsistenteIMSS.exe"; Description: "Iniciar Asistente IMSS"; Flags: nowait postinstall skipifsilent
~~~

3) Abre `installer\AsistenteIMSS.iss` en Inno Setup → **Compile**.  
   Salida: `installer\Output\AsistenteIMSS-Setup.exe`.

> **Variante Program Files (admin):** cambia `DefaultDirName={autopf}\Asistente IMSS` y `PrivilegesRequired=admin`.  
> Aun así, tu app debe guardar sesión/logs en `%LOCALAPPDATA%\AsistenteIMSS` (ya contemplado en tu código).

---

## Dónde se guardan los datos

- Sesión de WhatsApp, descargas temporales y log:  
  `%LOCALAPPDATA%\AsistenteIMSS`
- Esto evita permisos en *Program Files* y mantiene la sesión entre ejecuciones.

---

## Problemas comunes

- **“Qt platform plugin ‘windows’ no encontrado”**  
  Recompila el .exe incluyendo `--collect-all PyQt5`.

- **Pide QR cada vez**  
  Verifica que exista `%LOCALAPPDATA%\AsistenteIMSS\whatsapp_profile`.  
  Si borras esa carpeta, perderás la sesión.

- **Chrome / ChromeDriver incompatibles**  
  La primera ejecución descarga el ChromeDriver correspondiente al Chrome instalado.

- **Antivirus/SmartScreen advierte**  
  Normal en ejecutables nuevos sin firma. Puedes firmar el .exe y el Setup para distribución externa.

---

## Autor

Dember Salinas
; ===== Asistente IMSS - Instalador (Per-user, sin admin) =====
; Compila este script en Inno Setup para generar: installer\Output\AsistenteIMSS-Setup.exe
; Mantén el mismo AppId para futuras actualizaciones.

[Setup]
AppId={{8A23B90A-7F44-4C20-8F6E-4A3AD32B7A11}}
AppName=Asistente IMSS
AppVersion=1.0.2
AppPublisher=Tu Organización
AppPublisherURL=https://tu-dominio-ejemplo.com
AppSupportURL=https://tu-dominio-ejemplo.com/soporte

; Instalación por USUARIO (no requiere admin)
DefaultDirName={userappdata}\Asistente IMSS
DefaultGroupName=Asistente IMSS

OutputDir=installer\Output
OutputBaseFilename=AsistenteIMSS-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

; Icono del instalador (opcional). Usa app.ico si no tienes otro.
SetupIconFile=..\assets\app_setup.ico
UninstallDisplayIcon={app}\AsistenteIMSS.exe

; Evita advertencia si ya existe la carpeta destino
DirExistsWarning=no

[Files]
; Copia el ejecutable generado por PyInstaller
Source: "..\dist\AsistenteIMSS.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Carpeta de datos que usa tu app en %LOCALAPPDATA%
Name: "{localappdata}\AsistenteIMSS"

[Icons]
; Menú Inicio
Name: "{group}\Asistente IMSS"; Filename: "{app}\AsistenteIMSS.exe"; WorkingDir: "{app}"
; Acceso directo en Escritorio (opcional)
Name: "{userdesktop}\Asistente IMSS"; Filename: "{app}\AsistenteIMSS.exe"; Tasks: userdesktopicon; WorkingDir: "{app}"

[Tasks]
Name: "userdesktopicon"; Description: "Crear acceso directo en el Escritorio"; Flags: unchecked

[Run]
; Abrir la app al terminar la instalación
Filename: "{app}\AsistenteIMSS.exe"; Description: "Iniciar Asistente IMSS"; Flags: nowait postinstall skipifsilent

; --- Notas ---
; - Para actualizar: incrementa AppVersion pero conserva el mismo AppId.
; - Si prefieres instalar en Program Files (requiere admin):
;     DefaultDirName={autopf}\Asistente IMSS
;     PrivilegesRequired=admin
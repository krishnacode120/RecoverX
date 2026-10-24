[Setup]
AppId={{C10AD8DB-6AA1-4DC5-9206-01C180990B52}
AppName=RecoverX
AppVersion=0.3.0
AppPublisher=RecoverX
DefaultDirName={localappdata}\Programs\RecoverX
DefaultGroupName=RecoverX
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\..\dist\installer
OutputBaseFilename=RecoverX-Setup-0.3.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\RecoverX.exe
LicenseFile=..\..\..\THIRD_PARTY_NOTICES.md
[Files]
Source: "..\..\..\dist\RecoverX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\RecoverX"; Filename: "{app}\RecoverX.exe"
Name: "{group}\Uninstall RecoverX"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\RecoverX.exe"; Description: "Launch RecoverX"; Flags: nowait postinstall skipifsilent

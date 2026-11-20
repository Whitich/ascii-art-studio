#define AppVersion "1.2.0"
[Setup]
AppId={{B4F0400A-5E66-4534-B244-B3FB22BD064A}
AppName=ASCII Art Studio
AppVersion={#AppVersion}
AppPublisher=Whitich
AppPublisherURL=https://github.com/Whitich/ascii-art-studio
DefaultDirName={localappdata}\Programs\ASCII Art Studio
DefaultGroupName=ASCII Art Studio
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer-output
OutputBaseFilename=AsciiArtStudio-Setup-{#AppVersion}-win-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AsciiArtStudio.exe
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "dist\AsciiArtStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\ASCII Art Studio"; Filename: "{app}\AsciiArtStudio.exe"
Name: "{autodesktop}\ASCII Art Studio"; Filename: "{app}\AsciiArtStudio.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\AsciiArtStudio.exe"; Description: "Launch ASCII Art Studio"; Flags: nowait postinstall skipifsilent

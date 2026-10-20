#ifndef BuildRoot
  #error BuildRoot must be supplied by the reviewed build script
#endif
#ifdef ReviewBuild
  #define ProductName "MathStudio Recording Upgrade Review"
  #define ProductId "{{D7F3B29E-E2F1-41DA-B520-EA2E1F01B411}"
  #define InstallerName "MathStudio-Recording-Upgrade-Review"
#else
  #define ProductName "MathStudio"
  #define ProductId "{{E5935B86-2D46-45F3-8B46-E7A922F8A513}"
  #define InstallerName "MathStudio"
#endif
[Setup]
AppId={#ProductId}
AppName={#ProductName}
AppVersion=41.6.6
AppVerName={#ProductName} 41.6.6
AppPublisher=MathStudio project
DefaultDirName={localappdata}\Programs\{#ProductName}
DefaultGroupName={#ProductName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
OutputDir={#BuildRoot}\installer
OutputBaseFilename={#InstallerName}
SetupIconFile={#SourcePath}\generated\MathStudio.ico
UninstallDisplayIcon={app}\MathStudioClient.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion=41.6.6.0
VersionInfoDescription=MathStudio per-user teacher installer

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourcePath}\..\..\RECORDING_UPGRADE_REVIEW.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BuildRoot}\dist\MathStudioClient\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\{#ProductName}"; Filename: "{app}\MathStudioClient.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\{#ProductName}"; Filename: "{app}\MathStudioClient.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\MathStudioClient.exe"; Description: "{cm:LaunchProgram,{#ProductName}}"; Flags: nowait postinstall skipifsilent

; User settings are intentionally preserved on uninstall; no wildcard state deletion.

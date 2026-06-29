; Inno Setup Compiler Script for Research Paper Assistant Pro
; Uses lowest privilege to allow standard users to install without Admin prompts.

[Setup]
AppId={{D3B07A9F-2E11-4E62-81C5-A0175BDCC977}
AppName=Research Paper Assistant Pro
AppVersion=1.0.0
AppPublisher=Google DeepMind
DefaultDirName={localappdata}\ResearchPaperAssistantPro
DefaultGroupName=Research Paper Assistant Pro
OutputDir=..\
OutputBaseFilename=ResearchPaperAssistantSetup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableDirPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\ResearchPaperAssistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Research Paper Assistant Pro"; Filename: "{app}\ResearchPaperAssistant.exe"
Name: "{userdesktop}\Research Paper Assistant Pro"; Filename: "{app}\ResearchPaperAssistant.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ResearchPaperAssistant.exe"; Description: "{cm:LaunchProgram,Research Paper Assistant Pro}"; Flags: nowait postinstall skipifsilent

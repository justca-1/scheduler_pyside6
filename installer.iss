[Setup]
AppName=CCNHS Scheduler
AppVersion=1.0.0
AppPublisher=CCNHS
; Installs in the user's local AppData so it doesn't require Admin privileges
DefaultDirName={userappdata}\CCNHS Scheduler
DefaultGroupName=CCNHS Scheduler
OutputDir=.\dist
OutputBaseFilename=CCNHS_Scheduler_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
SetupIconFile=compiler:SetupClassicIcon.ico

[Files]
; Grabs everything PyInstaller created in the Scheduler folder
Source: "dist\Scheduler\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CCNHS Scheduler"; Filename: "{app}\Scheduler.exe"
Name: "{autodesktop}\CCNHS Scheduler"; Filename: "{app}\Scheduler.exe"
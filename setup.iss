; Inno Setup Script for CCNHS Scheduler

[Setup]
AppName=CCNHS Scheduler
AppVersion=1.0.0
DefaultDirName={autopf}\CCNHS Scheduler
DefaultGroupName=CCNHS Scheduler
OutputDir=.\installer
OutputBaseFilename=Scheduler_Setup
Compression=lzma2
SolidCompression=yes
; "lowest" allows installation without Admin rights if needed, change to "admin" to force Admin rights
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; This tells the installer to grab everything inside your PyInstaller output folder
Source: "dist\Scheduler\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\CCNHS Scheduler"; Filename: "{app}\Scheduler.exe"
Name: "{autodesktop}\CCNHS Scheduler"; Filename: "{app}\Scheduler.exe"; Tasks: desktopicon

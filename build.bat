@echo off
echo Cleaning old builds...
rmdir /s /q build
rmdir /s /q dist
del *.spec

echo Installing dependencies...
pip install --upgrade pyinstaller PySide6

echo Building executable...
python -m PyInstaller ^
--noconsole ^
--onedir ^
--name Scheduler ^
--clean ^
--collect-all PySide6 ^
--paths=scheduler_app\src ^
--add-data "scheduler_app\src\ui\*.qss;ui" ^
--add-data "scheduler_app\src\ui\icons;ui\icons" ^
scheduler_app\src\main.py

echo Building Windows Installer with Inno Setup...
:: This compiles the installer.iss file automatically
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

echo Done!
pause
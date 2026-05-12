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
scheduler_app\src\main.py

echo Done!
pause
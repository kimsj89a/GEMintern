@echo off
cd /d "%~dp0"

:: Clear Python cache to ensure latest code runs
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

call .venv\Scripts\activate.bat
python main.py
pause

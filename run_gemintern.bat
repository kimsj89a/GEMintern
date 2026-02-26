@echo off
chcp 65001 >nul
title GEM Intern v7.0
cd /d "%~dp0"
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
call .venv\Scripts\activate.bat
python -m backend.main --web

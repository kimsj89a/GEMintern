@echo off
chcp 65001 >nul
title GEM Intern v7.0
cd /d "%~dp0"
call .venv\Scripts\activate
python -m backend.main --web

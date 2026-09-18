@echo off
title Anonimizador Judicial - desarrollo
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno de desarrollo. Segui CONTRIBUTING.md para instalarlo.
  pause
  exit /b 1
)
echo Las aplicaciones abiertas se conservan. El servidor elige un puerto libre.
.venv\Scripts\python.exe scripts\run_dev.py
if errorlevel 1 pause

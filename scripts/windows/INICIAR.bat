@echo off
title Anonimizador Judicial - version actual
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
if errorlevel 1 (
  echo.
  pause
  exit /b 1
)

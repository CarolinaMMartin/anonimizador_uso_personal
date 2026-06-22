@echo off
title Anonimizador IALAB (desarrollo)
cd /d "%~dp0"

REM Cerrar ejecutables portables si quedaron abiertos
taskkill /IM AnonimizadorJudicial.exe /F >nul 2>&1
taskkill /IM AnonimizadorJudicial-NLP.exe /F >nul 2>&1

REM Liberar puerto 8787 (cualquier proceso que lo ocupe)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8787 ^| findstr LISTENING') do (
  taskkill /F /PID %%a >nul 2>&1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)

echo.
echo === Anonimizador IALAB - MODO DESARROLLO ===
echo Version mas reciente de interfaz y reglas.
echo URL: http://127.0.0.1:8787
echo Comprobar version: http://127.0.0.1:8787/health  (app_version debe ser 3.3.10)
echo.
echo NO uses la carpeta dist\ para probar cambios: usa ESTE INICIAR_DESARROLLO.bat.
echo No cierres esta ventana mientras uses la aplicacion.
echo.
.venv\Scripts\python scripts\run_dev.py
pause

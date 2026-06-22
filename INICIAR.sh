#!/bin/bash
# Desarrollo en macOS (requiere Python 3.11+)
cd "$(dirname "$0")"
lsof -ti:8787 | xargs kill -9 2>/dev/null || true

if [ ! -f ".venv/bin/python" ]; then
  echo "Creando entorno virtual..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

echo ""
echo "=== Anonimizador IALAB — desarrollo (macOS) ==="
echo "http://127.0.0.1:8787"
echo ""
.venv/bin/python scripts/run_dev.py

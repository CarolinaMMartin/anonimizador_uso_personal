#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "Falta el entorno de desarrollo. Segui CONTRIBUTING.md para instalarlo."
  exit 1
fi
echo "Las aplicaciones abiertas se conservan. El servidor elige un puerto libre."
exec .venv/bin/python scripts/run_dev.py

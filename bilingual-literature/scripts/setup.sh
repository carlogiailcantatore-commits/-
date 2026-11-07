#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="${BILINGUAL_VENV:-$ROOT/.venv}"
if command -v uv >/dev/null 2>&1; then
  uv venv "$VENV"
  uv pip install --python "$VENV/bin/python" python-docx lxml PyMuPDF openpyxl
else
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip
  "$VENV/bin/python" -m pip install python-docx lxml PyMuPDF openpyxl
fi
echo "VENV $VENV/bin/python"

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
BASE="$(pwd)"
EXTRA="${PYTHONPATH:+:$PYTHONPATH}"
echo 'Pruebas de regresión originales v16:'
PYTHONPATH="$BASE/desktop_reference:$BASE$EXTRA" python -m unittest discover -s desktop_reference -p 'test_*.py' -q
echo 'Pruebas del controlador Android con motor PC ACTUALIZADO:'
PYTHONPATH="$BASE/engine:$BASE$EXTRA" python -m unittest discover -s tests -p 'test_*.py' -q

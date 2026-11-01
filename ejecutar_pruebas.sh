#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
BASE="$(pwd)"
export PYTHONPATH="$BASE/engine:$BASE/desktop_reference:$BASE${PYTHONPATH:+:$PYTHONPATH}"
# Los tests legacy viven en desktop_reference, pero el motor ejecutable
# (logic.py, data.py, pactos.py) esta exclusivamente bajo engine/.
echo 'Pruebas de regresión del motor (incluidas las originales):'
python -m unittest discover -s desktop_reference -p 'test_*.py' -q
echo 'Pruebas del controlador Android y sincronización PC:'
python -m unittest discover -s tests -p 'test_*.py' -q

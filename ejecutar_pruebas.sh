#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/desktop_reference:$(pwd)/engine:$(pwd)${PYTHONPATH:+:$PYTHONPATH}"
echo 'Pruebas de regresión originales v16:'
python -m unittest discover -s desktop_reference -p 'test_*.py' -q
echo 'Pruebas nuevas del controlador Android:'
python -m unittest discover -s tests -p 'test_*.py' -q

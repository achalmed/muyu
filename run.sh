#!/usr/bin/env bash
# run.sh — lanzador de Muyu (la rueda universal): con el Python del sistema (PySide6 con Kirigami y layer-shell).
# Sin argumentos, la rueda vacía bajo el puntero; con archivos o enlaces, la rueda con ellos; --residente, la franja del
# borde; --instalar/--quitar, lo que pone en el escritorio de KDE (escritorio/__main__.py, `run.sh --help`).
set -euo pipefail
DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
export PYTHONPATH="${DIR}${PYTHONPATH:+:$PYTHONPATH}"
if [[ -z "${GUI_COMUN_DIR:-}" && -d "${DIR}/../gui-comun/gui_comun" ]]; then
    export GUI_COMUN_DIR="$(cd "${DIR}/../gui-comun" && pwd)"
fi
exec /usr/bin/python3 -m escritorio "$@"

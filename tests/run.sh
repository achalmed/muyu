#!/usr/bin/env bash
# tests/run.sh — las pruebas de Muyu: en proceso con el python3 que tenga pytest; la ventana (--smoke, --captura), en un
# proceso hijo con /usr/bin/python3 (el Qt con Kirigami). Carpeta temporal en disco; nada toca la sesión del usuario.
set -euo pipefail
DIR_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_TMP="${XDG_CACHE_HOME:-$HOME/.cache}/pytest/muyu"
mkdir -p "$BASE_TMP"
export PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen
if [[ -z "${GUI_COMUN_DIR:-}" && -d "${DIR_REPO}/../gui-comun/gui_comun" ]]; then
    export GUI_COMUN_DIR="$(cd "${DIR_REPO}/../gui-comun" && pwd)"
fi
exec python3 -m pytest "${DIR_REPO}/tests" --basetemp "$BASE_TMP" -p no:cacheprovider -q "$@"

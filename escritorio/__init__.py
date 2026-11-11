"""La ventana de Muyu: la rueda bajo el puntero (QML + Kirigami sobre gui-comun), con el Python del sistema (su
PySide6 es el que carga Kirigami y el módulo de layer-shell de KDE). La lógica sin Qt está en el paquete `muyu`.

`gui_comun` se localiza instalado (pip) o por `GUI_COMUN_DIR` (la carpeta del repo gui-comun, que `run.sh` pone si
está al lado): nunca subiendo carpetas.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ORG_NAME = "achalma"
VARIABLE_GUI_COMUN = "GUI_COMUN_DIR"


def hay_gui_comun() -> bool:
    try:
        import gui_comun  # noqa: F401
        return True
    except ImportError:
        pass
    carpeta = os.environ.get(VARIABLE_GUI_COMUN, "").strip()
    if carpeta and (Path(carpeta) / "gui_comun").is_dir():
        sys.path.append(carpeta)
        return True
    return False

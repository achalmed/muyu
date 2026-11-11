#!/usr/bin/python3
"""main.py — Muyu, la rueda universal (lo mismo que run.sh): con el Python del sistema, el que trae Kirigami."""
import os
import runpy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
if not os.environ.get("GUI_COMUN_DIR") and (REPO.parent / "gui-comun" / "gui_comun").is_dir():
    os.environ["GUI_COMUN_DIR"] = str(REPO.parent / "gui-comun")
runpy.run_module("escritorio", run_name="__main__")

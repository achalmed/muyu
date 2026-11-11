"""muyu/rutas.py — dónde está cada cosa, sin una sola ruta de la máquina escrita a mano (regla 2 de la guía raíz):

- la raíz del espacio de trabajo: `DOCS_ROOT`, o `gui_comun.rutas.docs_root()` (core/env.py), o la carpeta que
  contiene a Muyu;
- cada proyecto, por su `ruta` en `meta/workspace.yml` (el manifiesto único): si uno se renombra o se mueve, Muyu lo
  sigue encontrando; sin el manifiesto, la carpeta de su mismo nombre al lado;
- el intérprete y el corredor del motor de Raphi (su `.venv`), que es su API de proceso.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ESCRITORIO = REPO / "escritorio"


@lru_cache(maxsize=1)
def docs_root() -> Path:
    dicho = os.environ.get("DOCS_ROOT", "").strip()
    if dicho:
        return Path(dicho).expanduser()
    try:
        from gui_comun import rutas
        return Path(rutas.docs_root())
    except Exception:       # noqa: BLE001  fuera del espacio de trabajo o sin gui_comun
        return REPO.parent


@lru_cache(maxsize=1)
def _manifiesto() -> dict[str, str]:
    """{id: ruta} de meta/workspace.yml (vacío si no está o no se puede leer)."""
    ruta = docs_root() / "meta" / "workspace.yml"
    try:
        import yaml
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except Exception:       # noqa: BLE001
        return {}
    return {p["id"]: str(p.get("ruta", "")) for p in datos.get("proyectos", []) if isinstance(p, dict) and p.get("id")}


def proyecto(ident: str) -> Path:
    """La carpeta de un proyecto del espacio de trabajo (puede no existir: quien la usa lo comprueba)."""
    variable = "MUYU_" + ident.upper().replace("-", "_") + "_DIR"
    if os.environ.get(variable):
        return Path(os.environ[variable]).expanduser()
    ruta = _manifiesto().get(ident) or ident
    ruta = os.path.expandvars(ruta)
    p = Path(ruta).expanduser()
    return p if p.is_absolute() else docs_root() / p


def raphi_python() -> str:
    """El Python del motor de Raphi: `RAPHI_MOTOR_PYTHON` o el `.venv` de su repo."""
    dicho = os.environ.get("RAPHI_MOTOR_PYTHON", "").strip()
    if dicho and Path(dicho).is_file():
        return dicho
    return str(proyecto("raphi") / ".venv" / "bin" / "python")


def raphi_corredor() -> Path:
    return proyecto("raphi") / "escritorio" / "studio" / "corredor.py"


def hay_raphi() -> bool:
    return raphi_corredor().is_file() and Path(raphi_python()).is_file()


def config() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def datos() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def cache() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "muyu"

"""El proveedor «Abrir con…»: las aplicaciones que el sistema conoce para el tipo de los archivos (sus `.desktop` en
las carpetas XDG, con `MimeType=`), en el orden de tus preferencias (`mimeapps.list`: las predeterminadas y las
añadidas primero, sin las quitadas) y, la primera, la que era tu predeterminada antes de que Muyu lo fuera (la guarda
`muyu.instalar` al hacerlo predeterminado): con ella abre Intro.

Sin Qt: el tipo de un archivo lo da `QMimeDatabase` si el PySide6 del sistema está (con sus tipos padres: un .py
también es texto plano) o `xdg-mime`. Lanzar es expandir la línea `Exec` como dice la especificación de escritorio
(%f %F %u %U %i %c %k); `Terminal=true`, en Konsole.
"""
from __future__ import annotations

import configparser
import json
import os
import shlex
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from muyu import rutas

NOMBRE = "abrir"
PROPIO = ("muyu",)                          # Muyu no se ofrece a sí mismo
TOPE = 12


def carpetas_datos() -> list[Path]:
    base = [rutas.datos()] + [Path(d) for d in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":") if d]
    return list(dict.fromkeys(base))


def _leer_desktop(ruta: Path) -> dict | None:
    ini = configparser.ConfigParser(interpolation=None, strict=False, delimiters=("=",))
    ini.optionxform = str
    try:
        ini.read(ruta, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError, OSError):
        return None
    if not ini.has_section("Desktop Entry"):
        return None
    e = ini["Desktop Entry"]
    if e.get("Type", "Application") != "Application" or e.get("Hidden", "").lower() == "true" or not e.get("Exec"):
        return None
    if "KDE" in e.get("NotShowIn", "") or (e.get("OnlyShowIn") and "KDE" not in e.get("OnlyShowIn", "")):
        return None
    if e.get("TryExec") and not shutil.which(os.path.expanduser(e["TryExec"])):
        return None
    idioma = (os.environ.get("LANG") or "es").split(".")[0]

    def local(clave: str) -> str:
        for c in (f"{clave}[{idioma}]", f"{clave}[{idioma.split('_')[0]}]", clave):
            if e.get(c):
                return e[c]
        return ""
    return {"nombre": local("Name"), "generico": local("GenericName") or local("Comment"), "exec": e["Exec"],
            "icono": e.get("Icon", ""), "tipos": [t for t in e.get("MimeType", "").split(";") if t],
            "terminal": e.get("Terminal", "").lower() == "true", "ruta": str(ruta),
            "oculta": e.get("NoDisplay", "").lower() == "true"}


@lru_cache(maxsize=1)
def aplicaciones() -> dict[str, dict]:
    """{id de escritorio: datos} de todas las aplicaciones (las de la carpeta del usuario mandan sobre las del sistema)."""
    salida: dict[str, dict] = {}
    for base in carpetas_datos():
        carpeta = base / "applications"
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.rglob("*.desktop")):
            ident = str(ruta.relative_to(carpeta)).replace("/", "-")
            if ident in salida:
                continue
            datos = _leer_desktop(ruta)
            salida[ident] = datos if datos else {"oculta": True, "tipos": [], "anulada": True}
    return {k: v for k, v in salida.items() if not v.get("anulada")}


def _listas_mimeapps() -> list[Path]:
    escritorio = (os.environ.get("XDG_CURRENT_DESKTOP") or "KDE").split(":")[0].lower()
    rutas_ = []
    for base in [rutas.config()] + [Path(d) for d in (os.environ.get("XDG_CONFIG_DIRS") or "/etc/xdg").split(":")]:
        rutas_ += [base / f"{escritorio}-mimeapps.list", base / "mimeapps.list"]
    for base in carpetas_datos():
        rutas_ += [base / "applications" / f"{escritorio}-mimeapps.list", base / "applications" / "mimeapps.list"]
    return rutas_


@lru_cache(maxsize=1)
def preferencias() -> tuple[dict, dict, dict]:
    """(predeterminadas, añadidas, quitadas): {tipo: [ids]} de los mimeapps.list, el primero manda."""
    pred: dict[str, list[str]] = {}
    anad: dict[str, list[str]] = {}
    quit: dict[str, list[str]] = {}
    for ruta in _listas_mimeapps():
        ini = configparser.ConfigParser(interpolation=None, strict=False, delimiters=("=",))
        ini.optionxform = str
        try:
            ini.read(ruta, encoding="utf-8")
        except (configparser.Error, OSError, UnicodeDecodeError):
            continue
        for seccion, destino in (("Default Applications", pred), ("Added Associations", anad), ("Removed Associations", quit)):
            if ini.has_section(seccion):
                for tipo, valor in ini[seccion].items():
                    destino.setdefault(tipo, [])
                    destino[tipo] += [v for v in valor.split(";") if v and v not in destino[tipo]]
    return pred, anad, quit


def anteriores() -> dict[str, str]:
    """Lo que era predeterminado antes de que Muyu lo fuera ({tipo: id}), guardado por `muyu.instalar`."""
    try:
        return json.loads((rutas.config() / "muyu" / "predeterminadas.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def tipo_de(ruta: str) -> list[str]:
    """El tipo MIME de un archivo y sus padres (lo más concreto primero)."""
    try:
        from PySide6.QtCore import QMimeDatabase
        t = QMimeDatabase().mimeTypeForFile(ruta)
        return [t.name()] + [a for a in t.allAncestors() if a != t.name()]
    except ImportError:
        pass
    try:
        r = subprocess.run(["xdg-mime", "query", "filetype", ruta], capture_output=True, text=True, timeout=5)
        tipo = r.stdout.strip().split(";")[0]
    except (OSError, subprocess.SubprocessError):
        tipo = ""
    tipos = [tipo] if tipo else []
    if tipo.startswith("text/") and tipo != "text/plain":
        tipos.append("text/plain")
    return tipos + ["application/octet-stream"]


def apps_para(tipos: list[str]) -> list[str]:
    """Las aplicaciones para unos tipos (el primero, el del archivo; los demás, sus padres), en orden de preferencia."""
    pred, anad, quit = preferencias()
    todas = aplicaciones()
    previas = anteriores()
    orden: list[str] = []
    for tipo in tipos:
        candidatas = ([previas[tipo]] if tipo in previas else []) + pred.get(tipo, []) + anad.get(tipo, [])
        candidatas += sorted((i for i, a in todas.items() if tipo in a["tipos"]), key=lambda i: todas[i].get("oculta", False))
        for ident in candidatas:
            if ident in todas and ident not in orden and ident not in quit.get(tipo, []) and not ident.startswith(PROPIO):
                orden.append(ident)
    return orden


def opciones(rutas_: list[str]) -> list[dict]:
    """Un sector por aplicación que abre todos los archivos (la primera es la predeterminada). Nada para enlaces."""
    archivos = [r for r in rutas_ if not r.startswith(("http://", "https://"))]
    if not archivos or len(archivos) != len(rutas_):
        return []
    listas = [apps_para(tipo_de(r)) for r in archivos]
    comunes = [a for a in listas[0] if all(a in otra for otra in listas[1:])]
    todas = aplicaciones()
    salida = []
    for i, ident in enumerate(comunes[:TOPE]):
        app = todas[ident]
        salida.append({"proveedor": NOMBRE, "operacion": f"abrir:{ident}", "clave": f"abrir|{ident}", "a": None,
                       "anillo": "apps", "app": ident, "etiqueta": app["nombre"] or ident,
                       "titulo": f"Abrir con {app['nombre'] or ident}" + (" (la de siempre)" if i == 0 else ""),
                       "descripcion": app["generico"], "icono": app["icono"] or "application-x-executable",
                       "predeterminada": i == 0, "params": {}, "parametros": [], "pide": False, "fijos": [],
                       "categoria": "Abrir"})
    return salida


def _expandir(exec_: str, app: dict, archivos: list[str]) -> list[list[str]]:
    """La línea Exec con sus códigos (especificación de escritorio, «The Exec key»): una orden, o una por archivo si
    la aplicación recibe uno solo (%f, %u)."""
    try:
        partes = shlex.split(exec_.replace("%%", "\x00"))
    except ValueError:
        partes = exec_.split()
    urls = [Path(a).as_uri() if Path(a).exists() else a for a in archivos]
    varios = any(c in partes for c in ("%F", "%U"))
    uno = any(c in p for p in partes for c in ("%f", "%u"))

    def armar(lista_f: list[str], lista_u: list[str]) -> list[str]:
        orden: list[str] = []
        for p in partes:
            if p == "%F":
                orden += lista_f
            elif p == "%U":
                orden += lista_u
            elif p == "%i":
                orden += ["--icon", app["icono"]] if app.get("icono") else []
            else:
                p = p.replace("%f", lista_f[0] if lista_f else "").replace("%u", lista_u[0] if lista_u else "")
                p = p.replace("%c", app.get("nombre", "")).replace("%k", app.get("ruta", ""))
                for codigo in ("%d", "%D", "%n", "%N", "%v", "%m"):
                    p = p.replace(codigo, "")
                if p:
                    orden.append(p.replace("\x00", "%"))
        return orden
    if varios or not uno:
        ordenes = [armar(archivos, urls)]
        if not varios and not uno:                     # sin código: los archivos al final (lo que hace KDE)
            ordenes = [ordenes[0] + archivos]
    else:
        ordenes = [armar([f], [u]) for f, u in zip(archivos, urls)]
    if app.get("terminal"):
        ordenes = [["konsole", "-e", *o] for o in ordenes]
    return ordenes


def ordenes_para(ident: str, archivos: list[str]) -> list[list[str]]:
    app = aplicaciones().get(ident)
    if not app:
        raise LookupError(f"No hay una aplicación «{ident}».")
    return _expandir(app["exec"], app, archivos)

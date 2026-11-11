"""muyu/instalar.py — lo que Muyu pone en el escritorio de KDE, sin Qt; simula por omisión (regla 3 de la guía raíz):

- el acceso «Muyu» del menú de aplicaciones (`gui_comun.lanzador`, con su logo);
- «Abrir en Muyu…» en el clic derecho de Dolphin y de Krusader (un menú de servicio: Krusader los lee con
  KFileItemActions), para archivos y carpetas;
- el atajo global por omisión, Meta+Ctrl+R (`$XDG_DATA_HOME/kglobalaccel/muyu.desktop`, que KDE lee al entrar en la
  sesión; antes, se asigna en Preferencias del sistema › Atajos de teclado › Muyu);
- con `residente`, el inicio con la sesión: la franja del borde de la pantalla;
- si hay perfil de LibreOffice, la macro «Muyu» (Scripts/python/muyu.py): manda el documento abierto a la rueda;
- con `predeterminada`, Muyu como aplicación predeterminada de casi todos los tipos de archivo: antes respalda tu
  `mimeapps.list` y guarda la aplicación que tenía cada tipo (`predeterminadas.json`): esa es «la de siempre» en la
  rueda (Intro la abre) y `quitar` la devuelve. Nunca toma las carpetas, los enlaces web, los ejecutables ni los
  `.desktop` (Dolphin, el navegador y los lanzadores siguen como estaban).

Limpia también lo que puso la «Rueda de Raphi» (la rueda vivió en Raphi antes de ser Muyu). Quitar borra solo lo que
lleva la marca de Muyu.
"""
from __future__ import annotations

import configparser
import datetime as dt
import json
import shlex
import shutil
from pathlib import Path

from muyu import rutas

LANZADOR = rutas.REPO / "run.sh"
APP_ID = "muyu"
NOMBRE = "Muyu"
ATAJO = "Meta+Ctrl+R"
MARCA = "# Generado por Muyu (muyu/instalar.py); se quita con: muyu --quitar"
MARCAS_VIEJAS = ("# Generado por Raphi (escritorio/rueda/instalar.py)",)
# Lo que Muyu nunca toma como predeterminado
NO_TOMAR = ("inode/", "x-scheme-handler/", "x-content/", "application/x-desktop", "application/x-executable",
            "application/x-sharedlib", "application/x-shellscript", "application/x-ms-dos-executable",
            "application/vnd.flatpak", "application/x-pie-executable", "application/vnd.appimage", "application/x-iso9660-appimage")


def ruta_atajo() -> Path:
    return rutas.datos() / "kglobalaccel" / f"{APP_ID}.desktop"


def ruta_inicio() -> Path:
    return rutas.config() / "autostart" / f"{APP_ID}.desktop"


def ruta_menu() -> Path:
    return rutas.datos() / "kio" / "servicemenus" / f"{APP_ID}.desktop"


def perfil_libreoffice() -> Path:
    return rutas.config() / "libreoffice" / "4" / "user"


def ruta_macro() -> Path:
    return perfil_libreoffice() / "Scripts" / "python" / "muyu.py"


def ruta_preferencias() -> Path:
    return rutas.config() / "mimeapps.list"


def ruta_anteriores() -> Path:
    return rutas.config() / "muyu" / "predeterminadas.json"


def carpeta_respaldos() -> Path:
    """Los respaldos van a RESPALDOS_DIR (core/env) si el disco está; si no, a la configuración de Muyu.
    `MUYU_RESPALDOS_DIR` manda (las pruebas no tocan los respaldos de verdad)."""
    import os
    if os.environ.get("MUYU_RESPALDOS_DIR"):
        return Path(os.environ["MUYU_RESPALDOS_DIR"])
    try:
        from gui_comun import rutas as gr
        r = Path(gr.variable("RESPALDOS_DIR"))
        if r.is_dir():
            return r / "muyu"
    except Exception:   # noqa: BLE001
        pass
    return rutas.config() / "muyu" / "respaldos"


def _entrada(nombre: str, orden: list[str], extra: list[str]) -> str:
    return "\n".join([MARCA, "[Desktop Entry]", "Type=Application", f"Name={nombre}", f"Exec={shlex.join(orden)}",
                      f"Icon={APP_ID}", "Terminal=false", *extra]) + "\n"


def contenido_atajo() -> str:
    return _entrada(NOMBRE, [str(LANZADOR)], ["NoDisplay=true", f"X-KDE-Shortcuts={ATAJO}",
                                               "Comment=Abre la rueda bajo el puntero (también a mitad de un arrastre)"])


def contenido_inicio() -> str:
    return _entrada(f"{NOMBRE} (residente)", [str(LANZADOR), "--residente"],
                    ["NoDisplay=true", "X-KDE-autostart-phase=2", "Comment=La franja del borde que abre la rueda de Muyu"])


def contenido_menu() -> str:
    return "\n".join([MARCA, "[Desktop Entry]", "Type=Service", "MimeType=all/allfiles;inode/directory;",
                      "Actions=muyu;", "X-KDE-Priority=TopLevel", "", "[Desktop Action muyu]", "Name=Abrir en Muyu…",
                      f"Icon={APP_ID}", f"Exec={shlex.quote(str(LANZADOR))} %F", ""])


def contenido_macro() -> str:
    return f'''{MARCA}
"""Muyu desde LibreOffice: «muyu» manda el documento abierto (el archivo guardado) a la rueda, que aparece con él en
el centro: abrirlo con otra aplicación, a PDF, a otro formato de oficina, a Markdown, quitar sus metadatos… Póngala en
un menú o una barra: Herramientas › Personalizar › Macros de LibreOffice › Mis macros › muyu › muyu."""
import subprocess

import uno

LANZADOR = {str(LANZADOR)!r}


def _aviso(texto):
    contexto = XSCRIPTCONTEXT.getComponentContext()  # noqa: F821  (lo pone LibreOffice)
    kit = contexto.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", contexto)
    marco = XSCRIPTCONTEXT.getDesktop().getCurrentFrame()  # noqa: F821
    from com.sun.star.awt.MessageBoxType import INFOBOX
    kit.createMessageBox(marco.getContainerWindow() if marco else None, INFOBOX, 1, "Muyu", texto).execute()


def muyu(*_):
    documento = XSCRIPTCONTEXT.getDocument()  # noqa: F821
    url = documento.getURL() if documento is not None else ""
    if not url:
        _aviso("Guarde el documento primero: Muyu trabaja con el archivo guardado.")
        return
    if documento.isModified():
        _aviso("El documento tiene cambios sin guardar: Muyu usará la última versión guardada.")
    subprocess.Popen([LANZADOR, uno.fileUrlToSystemPath(url)], start_new_session=True)


g_exportedScripts = (muyu,)
'''


# --- la aplicación predeterminada -----------------------------------------------------------------------------------


def tipos_a_tomar() -> list[str]:
    """Los tipos que alguna aplicación del sistema abre, sin los que Muyu nunca toma."""
    from muyu.proveedores import abrir
    tipos = {t for app in abrir.aplicaciones().values() for t in app.get("tipos", [])}
    return sorted(t for t in tipos if "/" in t and not t.startswith(NO_TOMAR))


def _leer_ini(ruta: Path) -> configparser.ConfigParser:
    ini = configparser.ConfigParser(interpolation=None, strict=False, delimiters=("=",))
    ini.optionxform = str
    if ruta.is_file():
        ini.read(ruta, encoding="utf-8")
    return ini


def _escribir_ini(ini: configparser.ConfigParser, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        ini.write(f, space_around_delimiters=False)


def predeterminar(simular: bool = True) -> list[str]:
    from muyu.proveedores import abrir
    tipos = tipos_a_tomar()
    previas = abrir.anteriores()
    nuevas = {}
    for t in tipos:
        if t in previas:
            continue
        actual = next((a for a in abrir.apps_para([t]) if not a.startswith(APP_ID)), "")
        if actual:
            nuevas[t] = actual
    respaldo = carpeta_respaldos() / f"mimeapps.list.antes-muyu-{dt.datetime.now():%Y-%m-%d-%H%M%S}"
    hechos = [f"respaldo de {ruta_preferencias()} → {respaldo}",
              f"la aplicación de siempre de {len(nuevas) + len(previas)} tipos, guardada en {ruta_anteriores()}",
              f"Muyu, predeterminada para {len(tipos)} tipos (no carpetas, enlaces web, ejecutables ni .desktop)"]
    if simular:
        return hechos
    respaldo.parent.mkdir(parents=True, exist_ok=True)
    if ruta_preferencias().is_file():
        shutil.copy2(ruta_preferencias(), respaldo)
    ruta_anteriores().parent.mkdir(parents=True, exist_ok=True)
    ruta_anteriores().write_text(json.dumps({**previas, **nuevas}, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    ini = _leer_ini(ruta_preferencias())
    if not ini.has_section("Default Applications"):
        ini.add_section("Default Applications")
    for t in tipos:
        ini["Default Applications"][t] = f"{APP_ID}.desktop;"
    _escribir_ini(ini, ruta_preferencias())
    return hechos


def despredeterminar(simular: bool = True) -> list[str]:
    """Devuelve a cada tipo la aplicación que tenía antes de Muyu (o lo deja sin predeterminada)."""
    from muyu.proveedores import abrir
    previas = abrir.anteriores()
    ini = _leer_ini(ruta_preferencias())
    if not ini.has_section("Default Applications"):
        return []
    tomados = [t for t, v in ini["Default Applications"].items() if v.split(";")[0] == f"{APP_ID}.desktop"]
    if not tomados:
        return []
    hechos = [f"{len(tomados)} tipos vuelven a su aplicación de antes ({len([t for t in tomados if t in previas])} la tenían)"]
    if simular:
        return hechos
    for t in tomados:
        if previas.get(t):
            ini["Default Applications"][t] = previas[t] + ";"
        else:
            del ini["Default Applications"][t]
    _escribir_ini(ini, ruta_preferencias())
    return hechos


# --- instalar y quitar ----------------------------------------------------------------------------------------------


def _viejos() -> list[Path]:
    """Lo que puso la «Rueda de Raphi» (2026-11-10): se reemplaza por lo de Muyu."""
    candidatos = [rutas.datos() / "applications" / "raphi-rueda.desktop", rutas.datos() / "kglobalaccel" / "raphi-rueda.desktop",
                  rutas.config() / "autostart" / "raphi-rueda.desktop", perfil_libreoffice() / "Scripts" / "python" / "raphi.py"]
    salida = [p for p in candidatos if p.is_file() and any(m in p.read_text(encoding="utf-8", errors="ignore") for m in MARCAS_VIEJAS)]
    acceso = rutas.datos() / "applications" / "raphi-rueda.desktop"      # lo escribió gui_comun.lanzador, sin marca
    if acceso.is_file() and acceso not in salida and "run.sh rueda" in acceso.read_text(encoding="utf-8", errors="ignore"):
        salida.append(acceso)
    icono = rutas.datos() / "icons" / "hicolor" / "scalable" / "apps" / "raphi-rueda.svg"
    if icono.is_file():
        salida.append(icono)
    menu = rutas.datos() / "kio" / "servicemenus" / "raphi-rueda.desktop"
    if menu.is_file() and "rueda" in menu.read_text(encoding="utf-8", errors="ignore"):
        salida.append(menu)
    return salida


def instalar(residente: bool = False, predeterminada: bool = False, simular: bool = True) -> list[str]:
    """Lo que escribe (o escribiría): una línea por cosa."""
    viejos = _viejos()
    hechos = [f"quitar lo de la «Rueda de Raphi»: {p}" for p in viejos]
    if not simular:
        for p in viejos:
            p.unlink()
    tipos = tipos_a_tomar() if predeterminada else []
    try:
        from gui_comun import lanzador
        logo = (rutas.ESCRITORIO / "recursos" / "marca.svg").read_text(encoding="utf-8")
        hechas = lanzador.instalar(APP_ID, NOMBRE, "Abre, convierte y transforma cualquier archivo, carpeta o enlace", [str(LANZADOR)],
                                   logo_svg=logo, acento="violeta", categorias="Utility;", archivos=True,
                                   mimetypes="".join(f"{t};" for t in tipos),
                                   palabras="abrir;convertir;rueda;soltar;arrastrar;pdf;imagen;descargar;", simular=simular)
        hechos += [f"acceso del menú: {r}" for r in hechas]
    except ImportError:
        hechos.append("acceso del menú: sin gui_comun, no se pone (el resto sí)")
    escritos = [(ruta_menu(), contenido_menu(), "«Abrir en Muyu…» en Dolphin y Krusader", True),
                (ruta_atajo(), contenido_atajo(), f"atajo {ATAJO}", False)]
    if residente:
        escritos.append((ruta_inicio(), contenido_inicio(), "inicio con la sesión (residente)", False))
    if perfil_libreoffice().is_dir():
        escritos.append((ruta_macro(), contenido_macro(), "macro de LibreOffice «Muyu»", False))
    for ruta, texto, que, ejecutable in escritos:
        hechos.append(f"{que}: {ruta}")
        if not simular:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(texto, encoding="utf-8")
            if ejecutable:
                ruta.chmod(0o755)                    # Plasma 6 solo muestra menús de servicio ejecutables
    if predeterminada:
        hechos += predeterminar(simular)
    return hechos


def quitar(simular: bool = True) -> list[str]:
    hechos = despredeterminar(simular)
    for ruta in (ruta_atajo(), ruta_inicio(), ruta_macro(), ruta_menu()):
        if ruta.is_file() and MARCA in ruta.read_text(encoding="utf-8", errors="ignore"):
            hechos.append(f"quitado: {ruta}")
            if not simular:
                ruta.unlink()
    try:
        from gui_comun import lanzador
        hechos += [f"quitado: {r}" for r in lanzador.quitar(APP_ID, simular=simular)]
    except ImportError:
        pass
    return hechos

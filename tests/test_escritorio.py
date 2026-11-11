"""tests/test_escritorio.py — la rueda de Muyu con Qt: el controlador `Rueda` en proceso (los anillos que llegan del
corredor y su caché, correr un trabajo de verdad, encadenar con el resultado, volver, deshacer a la papelera, la vista
previa) y la ventana en un proceso hijo con el Python del sistema (`--smoke` y una captura con el panel de opciones
abierto). La papelera y la caché son temporales (XDG_DATA_HOME, XDG_CACHE_HOME); nada toca los archivos del usuario."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from conftest import PYTHON_SISTEMA, entorno_gui, requiere_qt as requiere_binding, requiere_raphi as requiere_motor, requiere_sistema


def _hasta(app, condicion, segundos=120):
    inicio = time.monotonic()
    while not condicion() and time.monotonic() - inicio < segundos:
        app.processEvents()
        time.sleep(0.03)
    app.processEvents()
    return condicion()


@pytest.fixture
def rueda(app, entorno):
    from gui_comun.tareas import Tareas
    from escritorio.controlador import Rueda
    tareas = Tareas(None)
    r = Rueda(tareas, entorno / "xdg_cache_home" / "muyu")
    yield r, tareas
    _hasta(app, lambda: not tareas.activa, 30)
    r.cerrar()
    app.processEvents()


def _sector(lista, etiqueta):
    return next(s for s in lista if s["etiqueta"] == etiqueta)


@requiere_binding
@requiere_motor
def test_anillos_trabajo_cadena_y_deshacer(app, rueda, muestra, entorno):
    r, tareas = rueda
    png = str(muestra["png"])
    r.cargar([png])
    assert _hasta(app, lambda: r.estado == "lista"), r.mensaje
    assert r.texto == Path(png).name and r.primeraEsImagen and r.interior[0]["etiqueta"] == "PDF"
    assert (entorno / "xdg_cache_home" / "muyu" / "opciones.json").is_file()        # la caché por extensiones

    # «Poner fondo» pide opciones (tiene un color): el panel, no el trabajo
    pedidos = []
    r.pedirOpciones.connect(lambda s: pedidos.append(s["etiqueta"]))
    fondo = _sector(r.exterior, "Poner fondo")
    r.elegir(fondo["clave"], False)
    assert pedidos == ["Poner fondo"] and r.estado == "lista"

    # la vista previa, en la caché y no junto al original
    r.previsualizar(fondo["clave"], {"proporcion": "1:1"})
    assert _hasta(app, lambda: r.vistaEstado in ("lista", "error")) and r.vistaEstado == "lista", r.vistaNota
    assert r.vistaTipo == "imagen" and "/muyu/vistas/" in r.vistaUrl and not r.viendoOriginal
    r.verOriginal(True)                                   # «Ver el original»: lo de entrada
    assert r.viendoOriginal and Path(png).name in r.vistaUrl
    r.verOriginal(False)

    # correr de verdad, y el resultado pasa al centro con sus anillos
    r.correr(fondo["clave"], {"proporcion": "1:1"})
    assert r.estado == "corriendo"
    assert _hasta(app, lambda: r.estado in ("hecha", "error") and not tareas.activa), r.mensaje
    assert r.estado == "hecha", r.mensaje
    salida = Path(r.resultados[0])
    assert salida.is_file() and salida.name.endswith("_con_fondo.png") and r.archivos == [str(salida)]
    assert r.hayHistorial and " › " in r.cadena and r.uriList.startswith("file://")

    # encadenar: un formato del resultado
    assert _hasta(app, lambda: bool(r.interior))
    r.elegir(_sector(r.interior, "JPG")["clave"], False)
    assert _hasta(app, lambda: r.estado == "hecha" and r.archivos[0].endswith(".jpg") and not tareas.activa), r.mensaje
    jpg = Path(r.archivos[0])

    # deshacer: el último resultado a la papelera (temporal) y de vuelta al anterior
    r.deshacer()
    assert not jpg.exists() and r.archivos == [str(salida)] and "papelera" in r.mensaje
    assert list((entorno / "xdg_data_home").rglob(jpg.name))
    # volver: al original, sin borrar nada
    r.volver()
    assert r.archivos == [png] and salida.exists() and not r.hayHistorial


@requiere_binding
@requiere_motor
def test_un_error_se_dice_y_no_cambia_el_centro(app, rueda, tmp_path):
    r, tareas = rueda
    roto = tmp_path / "roto.png"
    roto.write_bytes(b"no soy una imagen")
    r.cargar([str(roto)])
    assert _hasta(app, lambda: r.estado == "lista")
    r.correr(_sector(r.exterior, "Comprimir")["clave"], {})
    assert _hasta(app, lambda: r.estado in ("hecha", "error") and not tareas.activa)
    assert r.estado == "error" and "imagen" in r.mensaje and r.archivos == [str(roto)] and not r.hayHistorial


@requiere_binding
@requiere_motor
def test_mas_y_volver_cambian_el_anillo(app, rueda, muestra):
    r, _ = rueda
    r.cargar([str(muestra["pdf"])])
    assert _hasta(app, lambda: r.estado == "lista")
    mas = r.exterior[-1]
    assert mas["mas"] and mas["clave"] == "mas:exterior:1"
    primera = r.exterior[0]["etiqueta"]
    r.elegir(mas["clave"], False)
    assert r.exterior[-1]["clave"] == "volver:exterior:0" and not any(s["etiqueta"] == primera for s in r.exterior)
    r.elegir("volver:exterior:0", False)
    assert r.exterior[0]["etiqueta"] == primera


@requiere_sistema
def test_la_rueda_arranca(tmp_path, muestra):
    r = subprocess.run([PYTHON_SISTEMA, "-m", "escritorio", "--smoke"], env=entorno_gui(tmp_path),
                       capture_output=True, text=True, timeout=120, cwd=tmp_path)
    assert r.returncode == 0, r.stderr[-3000:]
    ruido = [l for l in r.stderr.splitlines() if ("TypeError" in l or "ReferenceError" in l) and "FormLayout.qml" not in l]
    assert not ruido, "\n".join(ruido)


@requiere_sistema
@requiere_motor
def test_captura_con_el_panel_de_opciones(tmp_path, muestra):
    captura = tmp_path / "rueda.png"
    antes = sorted(p.name for p in muestra["png"].parent.iterdir())
    env = entorno_gui(tmp_path, MUYU_PANEL="exterior:1", MUYU_ESPERA="4000")
    r = subprocess.run([PYTHON_SISTEMA, "-m", "escritorio", "--captura", str(captura), str(muestra["png"])], env=env,
                       capture_output=True, text=True, timeout=120, cwd=tmp_path)
    assert r.returncode == 0, r.stderr[-3000:]
    assert captura.is_file() and captura.stat().st_size > 20_000
    ruido = [l for l in r.stderr.splitlines() if ("TypeError" in l or "ReferenceError" in l) and "FormLayout.qml" not in l]
    assert not ruido, "\n".join(ruido)
    assert sorted(p.name for p in muestra["png"].parent.iterdir()) == antes      # la vista previa no escribe ahí


@requiere_binding
@requiere_motor
def test_un_informe_se_muestra(app, rueda, muestra):
    """Una herramienta de información (ver metadatos) no da archivo: deja su informe, en filas para leer."""
    r, tareas = rueda
    r.cargar([str(muestra["png"])])
    assert _hasta(app, lambda: r.estado == "lista")
    sector = next(s for s in r.exterior + r.sector("mas:exterior").get("hijos", []) if s["etiqueta"] == "Ver metadatos") \
        if any(s["etiqueta"] == "Ver metadatos" for s in r.exterior) else None
    if sector is None:                                    # tras «Más»
        r.elegir("mas:exterior", False)
        sector = next(s for s in r.exterior if s["etiqueta"] == "Ver metadatos")
    r.correr(sector["clave"], {})
    assert _hasta(app, lambda: r.estado in ("informe", "error") and not tareas.activa), r.mensaje
    assert r.estado == "informe", r.mensaje
    filas = r.informe[0]["filas"]
    assert filas and all(set(f) == {"clave", "valor"} for f in filas) and r.archivos == [str(muestra["png"])]


@requiere_binding
@requiere_motor
def test_un_enlace_y_sus_parametros(app, rueda):
    """Un enlace (sin red): sus anillos de calidades y maneras, y que el trabajo lleva el enlace en su parámetro."""
    r, _ = rueda
    r.cargar(["https://example.org/video?id=1", "/no/existe.pdf"])        # enlaces o archivos, no ambos
    assert r.sonEnlaces and r.archivos == ["https://example.org/video?id=1"] and r.texto == "example.org/video"
    if not _hasta(app, lambda: r.estado == "lista", 60):
        pytest.skip("sin yt-dlp: no hay opciones de descarga")
    assert [s["etiqueta"] for s in r.interior[:3]] == ["Mejor", "4K", "1080p"]
    sesion = next(s for s in r.exterior if s["etiqueta"] == "Con tu sesión…")
    assert sesion["pide"] and "url" in sesion["fijos"] and not r.tieneVista(sesion["clave"])
    params, archivos = r._params(sesion, {"cookies": "brave", "tramo": ""})
    assert archivos == [] and params["url"] == "https://example.org/video?id=1" and params["cookies"] == "brave"
    mp3 = next(s for s in r.interior if s["etiqueta"] == "MP3")
    params, _ = r._params(mp3, {"formato_audio": "wav"})                  # lo fijo de la opción manda
    assert params["formato_audio"] == "mp3" and params["modo"] == "audio"


@requiere_binding
def test_okular_y_portapapeles_sin_fallar(app, rueda, muestra):
    from escritorio.controlador import cerrar_a_la_izquierda, documentos_okular
    r, _ = rueda
    assert isinstance(documentos_okular(), list) and isinstance(cerrar_a_la_izquierda(), bool)
    r.refrescarOkular()
    assert r.paginaOkular == 0 or r.okular
    from gui_comun.qt import QGuiApplication
    QGuiApplication.clipboard().setText("nada útil aquí")
    r.pegar()
    assert "portapapeles" in r.mensaje
    QGuiApplication.clipboard().setText(str(muestra["pdf"]))
    r.pegar()
    assert r.archivos == [str(muestra["pdf"])]


@requiere_binding
def test_abrir_con_y_ordenes_de_un_proveedor(app, rueda, muestra, monkeypatch):
    """El anillo «Abrir con…» llega sin Raphi; abrir con una aplicación cierra la rueda; un proveedor de órdenes corre
    la suya y deja un informe (con su salida) o archivos nuevos (los de la carpeta que dijo)."""
    r, tareas = rueda
    from muyu import proveedores

    class Eco:
        NOMBRE = "eco"

        @staticmethod
        def opciones(rutas_):
            return [{"proveedor": "eco", "operacion": "eco:decir", "clave": "eco|decir", "a": None, "etiqueta": "Decir",
                     "titulo": "Decir algo", "params": {}, "parametros": [], "pide": False},
                    {"proveedor": "eco", "operacion": "eco:crear", "clave": "eco|crear", "a": None, "etiqueta": "Crear",
                     "titulo": "Crear un archivo", "params": {}, "parametros": [], "pide": False}]

        @staticmethod
        def preparar(s, params, archivos):
            carpeta = Path(archivos[0]).parent
            if s["operacion"] == "eco:decir":
                return {"argv": ["sh", "-c", "echo 'Tamaño: 4 GB'; echo listo"], "resultado": "informe"}
            return {"argv": ["sh", "-c", f"echo nuevo > '{carpeta}/creado.txt'"], "resultado": "archivos", "carpeta": str(carpeta)}

    monkeypatch.setattr(proveedores, "LOCALES", proveedores.LOCALES + [Eco])
    r.cargar([str(muestra["txt"])])
    assert _hasta(app, lambda: r.estado in ("lista", "error"), 60)
    assert {s["etiqueta"] for s in r._anillos["exterior"]} >= {"Decir", "Crear"}     # en alguna página
    r.correr("eco|decir", {})
    assert _hasta(app, lambda: r.estado == "informe" and not tareas.activa, 30), r.mensaje
    assert {"clave": "Tamaño", "valor": "4 GB"} in r.informe[0]["filas"]
    r.cargar([str(muestra["md"])])
    assert _hasta(app, lambda: r.estado == "lista", 60)
    r.correr("eco|crear", {})
    assert _hasta(app, lambda: r.estado == "hecha" and not tareas.activa, 30), r.mensaje
    assert r.archivos == [str(muestra["md"].parent / "creado.txt")] and r.hayHistorial
    # abrir con: una aplicación de mentira que no hace nada
    abiertos = []
    r.abierto.connect(abiertos.append)
    from muyu.proveedores import abrir
    monkeypatch.setattr(abrir, "ordenes_para", lambda ident, archivos: [["true", *archivos]])
    s = {"proveedor": "abrir", "app": "nada.desktop", "etiqueta": "Nada", "clave": "abrir|nada", "params": {}, "fijos": []}
    r._abrir_con(s, [str(muestra["md"])])
    assert abiertos == ["Nada"] and "Abierto con Nada" in r.mensaje

"""El paquete `muyu` sin ventana: los anillos, «Abrir con…» (con aplicaciones y preferencias de mentira en carpetas
XDG temporales), las rutas por el manifiesto, el instalador (simula por omisión; la predeterminada va y vuelve) y las
reglas: el paquete no importa Raphi ni a otro proyecto, la ventana no nombra operaciones ni trae colores propios."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from muyu import anillos, rutas
from muyu.proveedores import abrir

REPO = Path(__file__).resolve().parents[1]


def _app(carpeta: Path, ident: str, nombre: str, tipos: str, exec_: str = "", extra: str = "") -> None:
    (carpeta / "applications").mkdir(parents=True, exist_ok=True)
    (carpeta / "applications" / f"{ident}.desktop").write_text(
        f"[Desktop Entry]\nType=Application\nName={nombre}\nName[es]={nombre} (es)\nExec={exec_ or ident + ' %F'}\n"
        f"Icon={ident}\nMimeType={tipos}\n{extra}", encoding="utf-8")


@pytest.fixture
def apps(entorno, monkeypatch):
    datos = entorno / "xdg_data_home"
    sistema = entorno / "sistema"
    monkeypatch.setenv("XDG_DATA_DIRS", str(sistema))
    monkeypatch.setenv("XDG_CONFIG_DIRS", str(entorno / "etc"))
    monkeypatch.setenv("LANG", "es_PE.UTF-8")
    _app(sistema, "okular", "Okular", "application/pdf;", "okular %U")
    _app(sistema, "koreader", "KOReader", "application/pdf;", "koreader %f")
    _app(sistema, "kate", "Kate", "text/plain;", "kate -b %U")
    _app(sistema, "terminalera", "En terminal", "text/plain;", "vim", "Terminal=true\n")
    _app(sistema, "oculta", "Oculta", "application/pdf;", "x %f", "Hidden=true\n")
    _app(datos, "muyu", "Muyu", "application/pdf;text/plain;", "muyu %F")
    (entorno / "xdg_config_home" / "mimeapps.list").write_text(
        "[Default Applications]\napplication/pdf=koreader.desktop;\n[Removed Associations]\ntext/plain=terminalera.desktop;\n",
        encoding="utf-8")
    abrir.aplicaciones.cache_clear()
    abrir.preferencias.cache_clear()
    return entorno


# --- los anillos -----------------------------------------------------------------------------------------------------


def _opcion(op, a=None, **kw):
    return {"operacion": op, "a": a, "titulo": kw.pop("titulo", op.capitalize()), "params": kw.pop("params", {}),
            "parametros": kw.pop("parametros", []), **kw}


def test_anillos_reparte_ordena_y_pagina():
    opciones = [_opcion(f"convertir{i}", f) for i, f in enumerate(("bmp", "gif", "pdf", "docx", "tiff", "heic", "avif", "jpg", "png"))]
    opciones += [_opcion(f"herramienta{i}", titulo=f"Herramienta {i} PDF") for i in range(30)]
    opciones += [_opcion(f"abrir:{i}", anillo="apps", etiqueta=f"App {i}", proveedor="abrir", predeterminada=i == 0) for i in range(3)]
    a = anillos.construir(opciones)
    assert [s["etiqueta"] for s in a["interior"][:3]] == ["PDF", "DOCX", "JPG"]          # los más pedidos primero
    assert [s["etiqueta"] for s in a["apps"]] == ["App 0", "App 1", "App 2"] and a["apps"][0]["predeterminada"]
    tope = anillos.TOPE["exterior"]
    p0 = anillos.pagina(a["exterior"], "exterior", 0)
    assert len(p0) == tope and p0[-1]["clave"] == "mas:exterior:1" and p0[0]["etiqueta"] == "Herramienta 0"
    p1 = anillos.pagina(a["exterior"], "exterior", 1)
    assert len(p1) == tope and p1[-2]["clave"] == "mas:exterior:2" and p1[-1]["clave"] == "volver:exterior:0"
    vistos = [s["etiqueta"] for n in range(5) for s in anillos.pagina(a["exterior"], "exterior", n) if not s["mas"]]
    assert vistos[:30] == [f"Herramienta {i}" for i in range(30)]                       # cada una en alguna página, una vez
    ultima = anillos.pagina(a["exterior"], "exterior", 4)
    assert ultima[-1]["clave"] == "volver:exterior:3" and not any(x["clave"].startswith("mas:") for x in ultima)
    assert anillos.pagina(a["apps"], "apps", 0) == a["apps"]                              # si cabe, sin «Más»


def test_sector_respeta_lo_propio_de_la_opcion():
    o = _opcion("descargar", "mp4", etiqueta="1080p", titulo="Vídeo 1080p", clave="d|1080", enlace="url", fijos=["modo"],
                params={"modo": "video", "calidad": "1080"}, pide=False,
                parametros=[{"clave": "url", "etiqueta": "Enlaces", "tipo": "multilinea", "obligatorio": True},
                            {"clave": "tramo", "etiqueta": "Tramo", "tipo": "texto", "defecto": ""},
                            {"clave": "paginas", "etiqueta": "Páginas", "tipo": "paginas"}])
    s = anillos.sector(o)
    assert (s["etiqueta"], s["titulo"], s["clave"], s["pide"]) == ("1080p", "Vídeo 1080p", "d|1080", False)
    assert s["fijos"] == ["modo", "url"] and s["enlace"] == "url"
    assert {c["clave"]: c["tipo"] for c in s["campos"]}["paginas"] == "texto"
    sin_pide = anillos.sector(_opcion("tachar", parametros=[{"clave": "terminos", "etiqueta": "T", "tipo": "multilinea", "defecto": ""}]))
    assert sin_pide["pide"]                                          # un texto vacío por llenar: pregunta antes


def test_aplanar_y_filas_de_texto():
    filas = anillos.aplanar({"autor": "Ana", "paginas": [{"ancho": 595}], "listo": True, "tags": ["a", "b"]})
    assert {"clave": "autor", "valor": "Ana"} in filas and {"clave": "paginas › 1 › ancho", "valor": "595"} in filas
    assert {"clave": "listo", "valor": "sí"} in filas and {"clave": "tags", "valor": "a, b"} in filas
    texto = anillos.filas_de_texto(["Tamaño: 4 GB", "una línea suelta", "/ruta/a: algo"])
    assert texto[0] == {"clave": "Tamaño", "valor": "4 GB"} and texto[1]["clave"] == "" and texto[2]["clave"] == ""


def test_clave_de_cache_y_enlaces(tmp_path):
    assert anillos.clave_cache(["https://a.org/x"]) == "uno:enlaces"
    assert anillos.clave_cache([str(tmp_path / "a.PDF"), str(tmp_path)]) == "varios:.pdf,/"


# --- «Abrir con…» ----------------------------------------------------------------------------------------------------


def test_abrir_con_en_orden_de_preferencia(apps, tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    nombres = [o["etiqueta"] for o in abrir.opciones([str(pdf)])]
    assert nombres[0] == "KOReader (es)" and "Okular (es)" in nombres            # la predeterminada primero, en español
    assert not any("Muyu" in n or "Oculta" in n for n in nombres)                  # ni Muyu ni las ocultas
    (apps / "xdg_config_home" / "muyu").mkdir()
    (apps / "xdg_config_home" / "muyu" / "predeterminadas.json").write_text(json.dumps({"application/pdf": "okular.desktop"}))
    assert abrir.opciones([str(pdf)])[0]["etiqueta"] == "Okular (es)"             # la de antes de Muyu manda
    assert abrir.opciones(["https://a.org"]) == []


def test_abrir_con_quitadas_y_padres(apps, tmp_path):
    py = tmp_path / "x.txt"
    py.write_text("hola")
    nombres = [o["etiqueta"] for o in abrir.opciones([str(py)])]
    assert nombres == ["Kate (es)"]                                               # «En terminal» está quitada


def test_expandir_exec(apps):
    assert abrir.ordenes_para("koreader.desktop", ["/a b.pdf", "/c.pdf"]) == [["koreader", "/a b.pdf"], ["koreader", "/c.pdf"]]
    assert abrir.ordenes_para("okular.desktop", ["/a b.pdf"]) == [["okular", "file:///a%20b.pdf"]] or \
        abrir.ordenes_para("okular.desktop", ["/a b.pdf"])[0][0] == "okular"
    assert abrir.ordenes_para("terminalera.desktop", ["/n.txt"]) == [["konsole", "-e", "vim", "/n.txt"]]
    with pytest.raises(LookupError):
        abrir.ordenes_para("no-existe.desktop", ["/x"])


# --- las rutas -------------------------------------------------------------------------------------------------------


def test_proyecto_por_el_manifiesto(tmp_path, monkeypatch):
    (tmp_path / "meta").mkdir()
    (tmp_path / "meta" / "workspace.yml").write_text("proyectos:\n  - id: raphi\n    ruta: otra/raphi\n  - id: huella-datos\n    ruta: ~/osint\n")
    monkeypatch.setenv("DOCS_ROOT", str(tmp_path))
    rutas.docs_root.cache_clear()
    rutas._manifiesto.cache_clear()
    try:
        assert rutas.proyecto("raphi") == tmp_path / "otra" / "raphi"
        assert rutas.proyecto("huella-datos") == Path.home() / "osint"
        assert rutas.proyecto("git-studio") == tmp_path / "git-studio"
        monkeypatch.setenv("MUYU_RAPHI_DIR", str(tmp_path / "x"))
        assert rutas.proyecto("raphi") == tmp_path / "x"
    finally:
        rutas.docs_root.cache_clear()
        rutas._manifiesto.cache_clear()


# --- instalar --------------------------------------------------------------------------------------------------------


def test_instalar_simula_y_luego_va_y_vuelve(apps):
    from muyu import instalar
    config = apps / "xdg_config_home"
    antes = (config / "mimeapps.list").read_text()
    lineas = instalar.instalar(residente=True, predeterminada=True)
    assert any("Meta+Ctrl+R" in l for l in lineas) and any("predeterminada para" in l for l in lineas)
    assert (config / "mimeapps.list").read_text() == antes and not instalar.ruta_menu().exists()
    instalar.instalar(residente=True, predeterminada=True, simular=False)
    menu = instalar.ruta_menu()
    assert menu.stat().st_mode & 0o111 and "Abrir en Muyu" in menu.read_text()
    assert "X-KDE-Shortcuts=Meta+Ctrl+R" in instalar.ruta_atajo().read_text()
    escrito = (config / "mimeapps.list").read_text()
    assert "application/pdf=muyu.desktop;" in escrito and "text/plain=muyu.desktop;" in escrito
    previas = json.loads(instalar.ruta_anteriores().read_text())
    assert previas["application/pdf"] == "koreader.desktop" and previas["text/plain"] == "kate.desktop"
    assert list(instalar.carpeta_respaldos().glob("mimeapps.list.antes-muyu-*"))
    instalar.quitar(simular=False)
    vuelto = (config / "mimeapps.list").read_text()
    assert "application/pdf=koreader.desktop;" in vuelto and "muyu.desktop" not in vuelto
    assert not menu.exists() and not instalar.ruta_atajo().exists()


def test_nunca_toma_carpetas_ni_enlaces(apps):
    from muyu import instalar
    _app(apps / "sistema", "dolphin", "Dolphin", "inode/directory;x-scheme-handler/http;application/x-desktop;")
    abrir.aplicaciones.cache_clear()
    tipos = instalar.tipos_a_tomar()
    assert "application/pdf" in tipos and not [t for t in tipos if t.startswith(("inode/", "x-scheme-handler/"))]
    assert "application/x-desktop" not in tipos


def test_limpia_lo_de_la_rueda_de_raphi(apps):
    from muyu import instalar
    viejo = rutas.datos() / "kglobalaccel" / "raphi-rueda.desktop"
    viejo.parent.mkdir(parents=True)
    viejo.write_text("# Generado por Raphi (escritorio/rueda/instalar.py); x\n[Desktop Entry]\n")
    ajeno = rutas.datos() / "kglobalaccel" / "otro.desktop"
    ajeno.write_text("[Desktop Entry]\n")
    assert any("raphi-rueda" in l for l in instalar.instalar())
    instalar.instalar(simular=False)
    assert not viejo.exists() and ajeno.exists()


# --- las reglas ------------------------------------------------------------------------------------------------------


OTROS_PROYECTOS = ("raphi", "escritorio.studio", "git_app", "quarto", "latex", "huella", "filesystem", "tiqsi", "qillqa")


def test_el_paquete_no_importa_otros_proyectos_ni_qt_arriba():
    for archivo in (REPO / "muyu").rglob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in arbol.body:                                       # lo de arriba del módulo
            nombres = [a.name for a in nodo.names] if isinstance(nodo, ast.Import) else [nodo.module or ""] if isinstance(nodo, ast.ImportFrom) else []
            for n in nombres:
                assert not n.startswith(("PySide6", "PyQt6")), f"{archivo.name} importa {n} arriba"
        for nodo in ast.walk(arbol):
            nombres = [a.name for a in nodo.names] if isinstance(nodo, ast.Import) else [nodo.module or ""] if isinstance(nodo, ast.ImportFrom) else []
            for n in nombres:
                assert not n.startswith(OTROS_PROYECTOS), f"{archivo.name} importa {n}"


def test_la_ventana_no_trae_colores_propios_ni_importa_proyectos():
    for qml in (REPO / "escritorio" / "qml").glob("*.qml"):
        for n, linea in enumerate(qml.read_text(encoding="utf-8").splitlines(), 1):
            codigo = linea.split("//")[0]
            assert not re.search(r'"#[0-9a-fA-F]{3,8}"', codigo), f"{qml.name}:{n}"
            assert not re.search(r'\bfont\.(pointSize|pixelSize|family)\s*:\s*["\d]', codigo), f"{qml.name}:{n}"
    for archivo in (REPO / "escritorio").glob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                assert not nodo.module.startswith(OTROS_PROYECTOS), f"{archivo.name} importa {nodo.module}"

"""tests/conftest.py — utilidades de las pruebas de Muyu.

Dos clases de prueba, como en los studios: en proceso (el paquete `muyu`, el controlador) con el Python que corre
pytest, y en un proceso hijo (la ventana: `--smoke`, `--captura`) con el Python del sistema, el único cuyo Qt trae
Kirigami. Nada toca la configuración del usuario: XDG_CONFIG_HOME, XDG_DATA_HOME y XDG_CACHE_HOME van a temporales;
los archivos de muestra se escriben en cada prueba. Lo que necesita a Raphi (su corredor) se salta si Raphi no está.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if "GUI_COMUN_DIR" not in os.environ and (REPO.parent / "gui-comun" / "gui_comun").is_dir():
    os.environ["GUI_COMUN_DIR"] = str(REPO.parent / "gui-comun")

from escritorio import hay_gui_comun  # noqa: E402
from muyu import rutas  # noqa: E402

HAY_GUI_COMUN = hay_gui_comun()
HAY_BINDING = importlib.util.find_spec("PySide6") is not None
HAY_RAPHI = rutas.hay_raphi()
requiere_qt = pytest.mark.skipif(not (HAY_BINDING and HAY_GUI_COMUN), reason="sin PySide6 o sin gui_comun")
requiere_raphi = pytest.mark.skipif(not HAY_RAPHI, reason="sin Raphi (su corredor y su .venv) al lado")


def _python_del_sistema() -> str | None:
    if not Path("/usr/bin/python3").is_file() or not HAY_GUI_COMUN:
        return None
    r = subprocess.run(["/usr/bin/python3", "-c", "import PySide6.QtQml"], capture_output=True)
    return "/usr/bin/python3" if r.returncode == 0 else None


PYTHON_SISTEMA = _python_del_sistema()
requiere_sistema = pytest.mark.skipif(PYTHON_SISTEMA is None, reason="sin PySide6 con QML en /usr/bin/python3")

PDF_MINIMO = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
              b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\nxref\n0 4\n0000000000 65535 f \n"
              b"0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n164\n%%EOF\n")


@pytest.fixture
def muestra(tmp_path) -> dict[str, Path]:
    """Un PDF, un PNG, un texto, un Markdown y una carpeta, nuevos en cada prueba."""
    d = tmp_path / "muestra"
    d.mkdir()
    m = {"pdf": d / "oficio.pdf", "png": d / "foto.png", "txt": d / "nota.txt", "md": d / "guia.md", "carpeta": d / "carpeta"}
    m["pdf"].write_bytes(PDF_MINIMO)
    from PIL import Image
    Image.new("RGB", (64, 48), (46, 84, 150)).save(m["png"])
    m["txt"].write_text("hola\n", encoding="utf-8")
    m["md"].write_text("# Guía\n", encoding="utf-8")
    m["carpeta"].mkdir()
    return m


@pytest.fixture
def entorno(tmp_path, monkeypatch) -> Path:
    """La configuración, los datos y la caché del usuario, en temporales (no se toca la sesión de quien prueba)."""
    for nombre in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        carpeta = tmp_path / nombre.lower()
        carpeta.mkdir()
        monkeypatch.setenv(nombre, str(carpeta))
    monkeypatch.setenv("MUYU_RESPALDOS_DIR", str(tmp_path / "respaldos"))    # nunca los respaldos de verdad
    from muyu.proveedores import abrir
    abrir.aplicaciones.cache_clear()
    abrir.preferencias.cache_clear()
    return tmp_path


@pytest.fixture(scope="session")
def app():
    if not (HAY_BINDING and HAY_GUI_COMUN):
        pytest.skip("sin binding o sin gui_comun")
    from PySide6.QtGui import QGuiApplication
    yield QGuiApplication.instance() or QGuiApplication([sys.argv[0]])


def entorno_gui(tmp_path: Path, **extra: str) -> dict:
    env = dict(os.environ)
    env.update({"QT_QPA_PLATFORM": "offscreen", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(REPO),
                "XDG_CACHE_HOME": str(tmp_path / "cache-gui"), "XDG_CONFIG_HOME": str(tmp_path / "config-gui"),
                "XDG_RUNTIME_DIR": str(tmp_path / "runtime")})
    env.update(extra)
    return env

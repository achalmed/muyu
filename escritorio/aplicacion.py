"""escritorio/aplicacion.py — arma Muyu: la aplicación (gui_comun.nucleo), el controlador `Rueda`, la instancia única y
la ventana.

Cómo aparece (Wayland no deja a un programa ver un arrastre que empieza en otro, así que la rueda se llama):

- `muyu archivo…` — el doble clic en un archivo (Muyu es la aplicación predeterminada) o el menú de Dolphin y
  Krusader («Abrir en Muyu…»): la rueda con esos archivos en el centro, donde está el puntero, y la aplicación de
  siempre a un Intro;
- `muyu` — con un atajo global (Meta+Ctrl+R) en medio de un arrastre: la rueda aparece bajo el puntero y se suelta
  encima;
- `muyu --residente` — se queda en la sesión con una franja en el borde de la pantalla: arrastrar algo hasta el borde
  abre la rueda ahí mismo.

Si ya hay una rueda abierta (la residente, p. ej.), las llamadas siguientes le pasan los archivos por un socket local
y salen. En Wayland con el módulo QML de layer-shell de KDE, la ventana es una capa de superposición de toda la pantalla
(`QT_WAYLAND_SHELL_INTEGRATION=layer-shell`, antes de crear la aplicación); sin él, una ventana sin marco a pantalla
completa. La parte de la ventana que recibe el puntero es toda la pantalla mientras se espera algo y solo la rueda
mientras se arrastra un resultado fuera (`Mascara`): así se suelta sobre Dolphin, que está debajo.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from escritorio import ORG_NAME, hay_gui_comun

APP_DIR = Path(__file__).resolve().parent
QML_DIR = APP_DIR / "qml"
APP_ID = "muyu"
NOMBRE = "Muyu"


def ruta_socket() -> str:
    """El socket de la instancia única, en la carpeta de ejecución del usuario (una ruta absoluta: QLocalServer la
    usa tal cual y el cliente se conecta con el `socket` de Python, sin crear una aplicación de Qt antes de tiempo)."""
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/raphi-{os.getuid()}"
    Path(base).mkdir(parents=True, exist_ok=True)
    return str(Path(base) / "muyu.sock")


def hay_capa() -> bool:
    """¿Wayland con el módulo QML de layer-shell (org.kde.layershell)? Se mira el disco: aún no hay aplicación."""
    if os.environ.get("MUYU_SIN_CAPA") or os.environ.get("QT_QPA_PLATFORM", "").startswith("offscreen"):
        return False
    if os.environ.get("XDG_SESSION_TYPE") != "wayland" and not os.environ.get("WAYLAND_DISPLAY"):
        return False
    try:
        from PySide6.QtCore import QLibraryInfo
        qml = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.QmlImportsPath))
    except Exception:   # noqa: BLE001
        return False
    return (qml / "org" / "kde" / "layershell" / "qmldir").is_file()


PROPIAS = ("QT_WAYLAND_SHELL_INTEGRATION", "GUI_COMUN_DIR", "MUYU_SIN_CAPA", "MUYU_PANEL", "MUYU_ESPERA")


def entorno_limpio(entorno: dict[str, str]) -> dict[str, str]:
    """El entorno de lo que Muyu lanza: sin lo que solo le sirve a Muyu. Con la variable de layer-shell, una aplicación
    de Qt (Gwenview, Okular…) nacería como capa de superposición: sin marco, sin botones y encima de todo; con la
    carpeta de Muyu en PYTHONPATH, un programa en Python podría importar sus paquetes en vez de los suyos."""
    limpio = {k: v for k, v in entorno.items() if k not in PROPIAS}
    if limpio.get("PYTHONPATH"):
        partes = [x for x in limpio["PYTHONPATH"].split(os.pathsep) if x and Path(x).resolve() != Path(__file__).resolve().parents[1]]
        if partes:
            limpio["PYTHONPATH"] = os.pathsep.join(partes)
        else:
            del limpio["PYTHONPATH"]
    return limpio


def limpiar_entorno() -> None:
    """Quita del entorno de este proceso lo de `entorno_limpio` (los procesos hijos lo heredan)."""
    limpio = entorno_limpio(dict(os.environ))
    for clave in [k for k in os.environ if k not in limpio]:
        del os.environ[clave]
    if "PYTHONPATH" in limpio:
        os.environ["PYTHONPATH"] = limpio["PYTHONPATH"]


def mandar_a_la_abierta(archivos: list[str], mostrar: bool) -> bool:
    """Si hay una rueda abierta, le pasa los archivos (y que se muestre) y devuelve True."""
    import socket
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect(ruta_socket())
            s.sendall(json.dumps({"archivos": archivos, "mostrar": mostrar}).encode("utf-8"))
        except OSError:
            return False
    return True


def main(argv: list[str]) -> int:
    humo = "--smoke" in argv
    residente = "--residente" in argv
    captura = next((argv[i + 1] for i, a in enumerate(argv) if a == "--captura" and i + 1 < len(argv)), "")
    archivos = [a if a.startswith(("http://", "https://")) else str(Path(a).resolve()) for i, a in enumerate(argv)
                if not a.startswith("--") and (i == 0 or argv[i - 1] != "--captura")]
    if not humo and not captura and mandar_a_la_abierta(archivos, True):
        return 0
    capa = hay_capa() and not humo
    if capa:
        os.environ["QT_WAYLAND_SHELL_INTEGRATION"] = "layer-shell"
    if not hay_gui_comun():
        print("muyu: falta gui_comun (pip install gui-comun, o GUI_COMUN_DIR)", file=sys.stderr)
        return 1

    from gui_comun.nucleo import Aplicacion
    from gui_comun.qt import QObject, QTimer, Slot
    from gui_comun.tareas import Tareas
    from PySide6.QtGui import QRegion
    from PySide6.QtNetwork import QLocalServer

    from escritorio.controlador import Rueda
    from muyu import rutas

    app = Aplicacion(APP_ID, NOMBRE, organizacion=ORG_NAME, argv=[sys.argv[0]])
    limpiar_entorno()                 # Qt ya leyó la capa: lo que Muyu lance después nace sin ella
    app.app.setQuitOnLastWindowClosed(False)
    cache = rutas.cache()
    tareas = Tareas(None)
    rueda = Rueda(tareas, cache, notificador=app.notificador)
    rueda.terminado.connect(rueda.avisar)

    class Ventana(QObject):
        """Lo que el QML pide a su ventana y no puede hacer solo: la máscara de entrada, salir."""

        @Slot(int, int, int, int)
        def soloCirculo(self, x: int, y: int, ancho: int, alto: int) -> None:  # noqa: N802
            v = app.ventana()
            if v is not None:
                v.setMask(QRegion(x, y, ancho, alto, QRegion.RegionType.Ellipse))

        @Slot()
        def todaLaPantalla(self) -> None:  # noqa: N802
            v = app.ventana()
            if v is not None:
                v.setMask(QRegion())

        @Slot()
        def ocultada(self) -> None:
            """La rueda se cerró: la residente se queda; la otra sale cuando no queda trabajo."""
            rueda.fijarVisible(False)
            if residente:
                if rueda.estado != "corriendo":
                    rueda.vaciar()
                return
            if rueda.estado != "corriendo":
                app.app.quit()
            else:
                rueda.terminado.connect(lambda *_: QTimer.singleShot(4000, app.app.quit))

    ventana = Ventana()
    app.exponer("rueda", rueda)
    app.exponer("ventanaRueda", ventana)
    app.exponer("tareasRueda", tareas)
    app.motor.rootContext().setContextProperty("residente", residente)
    app.motor.rootContext().setContextProperty("conCapa", capa)
    app.motor.rootContext().setContextProperty("inicialVisible", not residente or bool(archivos))
    app.motor.rootContext().setContextProperty("pruebaPanel", os.environ.get("MUYU_PANEL", "") if captura or humo else "")

    servidor = QLocalServer()
    if not humo and not captura:
        QLocalServer.removeServer(ruta_socket())
        servidor.listen(ruta_socket())

    def llegada() -> None:
        socket = servidor.nextPendingConnection()

        def leer(s=socket) -> None:
            try:
                datos = json.loads(bytes(s.readAll()).decode("utf-8") or "{}")
            except ValueError:
                return
            if datos.get("archivos"):
                rueda.cargar(datos["archivos"])
            if datos.get("mostrar"):
                rueda.mostrar.emit()
        socket.readyRead.connect(leer)
    servidor.newConnection.connect(llegada)

    if archivos:
        rueda.cargar(archivos)
    raiz = QML_DIR / ("SuperposicionCapa.qml" if capa else "Superposicion.qml")
    if captura:
        app.capturar(captura, espera_ms=int(os.environ.get("MUYU_ESPERA", "2500")))
    app.app.aboutToQuit.connect(rueda.cerrar)
    return app.ejecutar(raiz, humo=humo)

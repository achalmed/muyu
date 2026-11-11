"""escritorio/controlador.py — `Rueda`, lo que la rueda de Muyu ve desde QML: los archivos del centro, los dos
anillos, el trabajo en curso con su progreso, el resultado (que se arrastra fuera o sigue en la rueda) y la vista
previa en vivo de las opciones.

Lo que se ofrece viene de los proveedores (`muyu/proveedores/`): el motor de Raphi por su corredor, en otro proceso con
su `.venv` (`rueda <archivos…>` con caché por extensiones; `ejecutar`, `vista` y `actuales`), y los que se calculan
aquí («Abrir con…», los studios, el sistema). Cada trabajo se corre según su proveedor: abrir una aplicación, el
corredor de Raphi, o la orden que prepara el proveedor (con `gui_comun.tareas`: Esc lo cancela con todo su grupo de
procesos). La rueda no nombra ninguna operación (`muyu/anillos.py`).

Encadenar: al terminar bien, el resultado pasa a ser lo que hay en el centro y los anillos se rehacen para su tipo
(de PDF a JPG y, sin soltar, a recortar o a poner fondo). «Deshacer» manda el resultado a la papelera y vuelve al
archivo anterior; «Volver», sin borrar nada.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from gui_comun.qt import QObject, QProcess, QUrl, Property, Signal, Slot, es_valido

from muyu import anillos, proveedores, rutas
from muyu.proveedores import abrir
from muyu.proveedores import raphi as prov_raphi

# Las categorías del motor cuya vista previa es barata y dice algo (las que dibujan sobre el archivo); en una imagen,
# todas. Comprimir un PDF con Ghostscript o pasarle OCR para una vista previa costaría lo que el trabajo mismo.
VISTA_EN_PDF = {"Editar", "Seguridad", "Organizar"}
VISTA_DE_PDF = {"txt", "md", "html", "png", "jpg", "srt", "vtt"}     # de un PDF o un texto: se ve el texto o la imagen
LADO_VISTA = 1400


def tipo_vista(ruta: str) -> str:
    """Cómo se ve un archivo en el panel: imagen, pdf, texto o "" (no se puede ver aquí)."""
    ext = Path(ruta).suffix.lower()
    if anillos.es_imagen(ruta) and ext not in (".heic", ".heif", ".avif"):
        return "imagen"
    if ext == ".pdf":
        return "pdf"
    return "texto" if ext in anillos.EXT_TEXTO else ""


def documentos_okular() -> list[dict]:
    """Lo que cada Okular abierto está mostrando (D-Bus: org.kde.okular-<pid>, /okular): [{ruta, nombre, pagina}].
    Llamadas directas con un tope de 0,8 s (sin la introspección de QDBusInterface, que puede bloquear 25 s si un
    Okular no responde): la rueda lo pide cada vez que aparece. Vacío sin Okular o sin QtDBus."""
    try:
        from PySide6.QtDBus import QDBus, QDBusConnection, QDBusMessage
    except ImportError:
        return []
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        return []

    def llamar(servicio: str, metodo: str):
        respuesta = bus.call(QDBusMessage.createMethodCall(servicio, "/okular", "org.kde.okular", metodo), QDBus.CallMode.Block, 800)
        argumentos = respuesta.arguments() if respuesta.type() == QDBusMessage.MessageType.ReplyMessage else []
        return argumentos[0] if argumentos else None

    salida = []
    for servicio in bus.interface().registeredServiceNames().value() or []:
        if not servicio.startswith("org.kde.okular-"):
            continue
        ruta = str(llamar(servicio, "currentDocument") or "")
        pagina = llamar(servicio, "currentPage")
        if ruta.startswith("file:"):
            ruta = QUrl(ruta).toLocalFile()
        if ruta and Path(ruta).is_file():
            salida.append({"ruta": ruta, "nombre": Path(ruta).name, "pagina": int(pagina or 0),     # Okular cuenta desde 1
                           "servicio": servicio})
    return salida


def lanzar(argv: list[str], cwd: str = "") -> bool:
    """Una aplicación suelta (abrir con, Dolphin, QEMU, Konsole): sin heredar la salida de Muyu."""
    from gui_comun.qt import QProcess as P
    proceso = P()
    proceso.setProgram(argv[0])
    proceso.setArguments(argv[1:])
    if cwd:
        proceso.setWorkingDirectory(cwd)
    proceso.setStandardOutputFile(P.nullDevice())
    proceso.setStandardErrorFile(P.nullDevice())
    resultado = proceso.startDetached()                  # PySide6 devuelve (ok, pid)
    return bool(resultado[0] if isinstance(resultado, tuple) else resultado)


def cerrar_a_la_izquierda() -> bool:
    """¿La decoración de ventanas de KWin pone «cerrar» a la izquierda (ButtonsOnLeft con X, como macOS)? El botón de
    cerrar del panel va en el mismo lado y con el mismo aspecto que el de las ventanas."""
    import configparser
    import os
    kwinrc = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "kwinrc"
    ini = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        ini.read(kwinrc, encoding="utf-8")
        return "X" in ini.get("org.kde.kdecoration2", "ButtonsOnLeft", fallback="")
    except (configparser.Error, OSError):
        return False


def ruta_de(texto: str) -> str:
    """Una ruta local desde lo que llega de QML: una URL file:// o una ruta."""
    if texto.startswith("file:"):
        return QUrl(texto).toLocalFile()
    return str(Path(texto).expanduser())


def huella_motor() -> str:
    """Cambia cuando cambia el motor: la versión de la caché de anillos."""
    carpeta = rutas.proyecto("raphi") / "raphi" / "motor"
    corredor = rutas.raphi_corredor()
    marcas = [int(p.stat().st_mtime) for p in carpeta.glob("*.py")] + ([int(corredor.stat().st_mtime)] if corredor.is_file() else [])
    return str(max(marcas, default=0))


class Rueda(QObject):
    cambiada = Signal()
    vistaCambiada = Signal()
    pedirOpciones = Signal("QVariantMap")         # un sector que pide opciones o tiene editor: QML abre el panel
    terminado = Signal(bool, str)                 # ok, mensaje (la notificación si la rueda ya no se ve)
    mostrar = Signal()                            # otra llamada (Dolphin, el atajo) pide ver la rueda
    valoresActuales = Signal(str, "QVariantMap")  # clave del sector, lo que el archivo ya tiene (rellenar el panel)
    abierto = Signal(str)                         # se abrió con una aplicación: la rueda se cierra

    def __init__(self, tareas, cache: Path, notificador=None, parent=None):
        super().__init__(parent)
        self._tareas = tareas
        self._notificador = notificador
        self._cache = cache
        (cache / "trabajos").mkdir(parents=True, exist_ok=True)
        (cache / "vistas").mkdir(parents=True, exist_ok=True)
        self._huella = huella_motor()
        self._ruta_anillos = cache / "opciones.json"
        self._memoria = self._leer_cache()
        self._archivos: list[str] = []
        self._historial: list[list[str]] = []
        self._anillos: dict = {"interior": [], "exterior": [], "apps": []}
        self._en_mas = {"interior": 0, "exterior": 0, "apps": 0}
        self._locales: list[dict] = []    # lo que dan los proveedores de este proceso para lo del centro
        self._estado = "vacia"            # vacia · cargando · lista · corriendo · hecha · error
        self._progreso = 0
        self._mensaje = ""
        self._resultados: list[str] = []
        self._titulo_trabajo = ""
        self._proceso_anillos: QProcess | None = None
        self._pendiente = ""              # una clave soltada antes de que llegaran los anillos
        self._proceso_vista: QProcess | None = None
        self._vista_archivo = ""          # la salida prevista, en la caché
        self._vista_tipo = ""             # imagen · pdf · texto · ""
        self._vista_estado = ""           # "" · cargando · lista · sin · error
        self._vista_nota = ""
        self._ver_original = False
        self._n_vista = 0
        self._informe: list[dict] = []    # lo que dijo un trabajo de información: [{entrada, filas: [{clave, valor}]}]
        self._cerrar_izquierda = cerrar_a_la_izquierda()
        self._okular: list[dict] = []
        try:
            from gui_comun.visor_pdf import VisorPdf
            self._visor = VisorPdf(cache / "visor", variable_motor="RAPHI_VISOR", parent=self)
        except Exception:   # noqa: BLE001  sin el visor de PDF, la vista de un PDF dice que no se puede ver aquí
            self._visor = None
        self._visible = False
        self._anillos = anillos.construir(proveedores.locales([]))

    def cerrar(self) -> None:
        """Al salir (la aplicación, una prueba): los procesos en marcha se matan y se esperan, para que su fin no
        llegue a un controlador que ya no existe."""
        for proceso in (self._proceso_anillos, self._proceso_vista):
            if proceso is not None and es_valido(proceso):
                proceso.blockSignals(True)
                proceso.kill()
                proceso.waitForFinished(3000)
        self._proceso_anillos = self._proceso_vista = None

    # ------------------------------------------------------------------------------------------------ caché
    def _leer_cache(self) -> dict:
        try:
            datos = json.loads(self._ruta_anillos.read_text(encoding="utf-8"))
            return datos.get("opciones", {}) if datos.get("huella") == self._huella else {}
        except (OSError, ValueError):
            return {}

    def _guardar_cache(self) -> None:
        try:
            self._ruta_anillos.write_text(json.dumps({"huella": self._huella, "opciones": self._memoria}, ensure_ascii=False),
                                          encoding="utf-8")
        except OSError:
            pass

    # ------------------------------------------------------------------------------------------------ archivos
    @Slot("QVariantList")
    def cargar(self, lista) -> None:
        """Lo soltado o lo pasado por la línea de órdenes pasa al centro (si cambió) y se piden sus anillos."""
        nuevas = [str(x).strip() if anillos.es_enlace(str(x).strip()) else ruta_de(str(x)) for x in (lista or []) if str(x).strip()]
        enlaces = list(dict.fromkeys(r for r in nuevas if anillos.es_enlace(r)))
        nuevas = enlaces or [r for r in nuevas if Path(r).exists()]      # enlaces del navegador o archivos, no ambos
        if not nuevas:
            return
        if nuevas == self._archivos and self._estado in ("lista", "cargando", "hecha"):
            return
        if self._estado == "corriendo":
            return
        self._archivos = nuevas
        self._resultados = []
        self._informe = []
        self._mensaje = ""
        self._pedir_anillos()

    def _pedir_anillos(self) -> None:
        self._en_mas = {"interior": 0, "exterior": 0, "apps": 0}
        self.limpiarVista()
        self._locales = proveedores.locales(self._archivos)
        clave = anillos.clave_cache(self._archivos)
        if not prov_raphi.disponible():
            self._poner_anillos(anillos.construir(self._locales))
            return
        if clave in self._memoria:
            self._poner_anillos(anillos.construir(prov_raphi.marcar(self._memoria[clave]) + self._locales))
            return
        if self._locales:                     # lo local (abrir con, los studios) se ve ya; lo de Raphi llega después
            self._anillos = anillos.construir(self._locales)
        if self._estado != "hecha":           # con un resultado recién hecho, el centro lo sigue mostrando mientras tanto
            self._estado = "cargando"
        self.cambiada.emit()
        if self._proceso_anillos is not None:
            self._proceso_anillos.kill()
        proceso = QProcess(self)
        self._proceso_anillos = proceso
        pedidas = list(self._archivos)
        proceso.finished.connect(lambda codigo, _estado, p=proceso, c=clave, pe=pedidas: self._anillos_llegaron(p, c, pe, codigo))
        orden = prov_raphi.orden("rueda", *pedidas)
        proceso.start(orden[0], orden[1:])

    def _anillos_llegaron(self, proceso: QProcess, clave: str, pedidas: list[str], codigo: int) -> None:
        if not es_valido(proceso) or not es_valido(self):   # al cerrar la aplicación con el proceso en marcha
            return
        proceso.deleteLater()
        if proceso is not self._proceso_anillos:
            return
        self._proceso_anillos = None
        salida = bytes(proceso.readAllStandardOutput()).decode("utf-8", "replace")
        try:
            opciones = json.loads(salida)["opciones"] if codigo == 0 else None
        except (ValueError, KeyError):
            opciones = None
        if opciones is None:
            error = bytes(proceso.readAllStandardError()).decode("utf-8", "replace").strip().splitlines()
            self._mensaje = "Raphi no respondió" + (f": {error[-1]}" if error else ".")
            self._poner_anillos(anillos.construir(self._locales))     # sin Raphi, lo demás sigue
            return
        self._memoria[clave] = opciones           # lo crudo del motor: los anillos se arman cada vez (anillos.py puede cambiar)
        self._guardar_cache()
        if pedidas == self._archivos:
            self._poner_anillos(anillos.construir(prov_raphi.marcar(opciones) + self._locales))

    def _poner_anillos(self, construidos: dict) -> None:
        self._anillos = construidos
        if self._estado != "hecha":
            self._estado = "lista"
        self.cambiada.emit()
        if self._pendiente:
            clave, self._pendiente = self._pendiente, ""
            self.elegir(clave, False)

    @Slot()
    def vaciar(self) -> None:
        if self._estado == "corriendo":
            return
        self._archivos, self._resultados, self._historial = [], [], []
        self._anillos = anillos.construir(proveedores.locales([]))      # la rueda vacía: las herramientas generales
        self._estado, self._mensaje = "vacia", ""
        self.limpiarVista()
        self.cambiada.emit()

    # ------------------------------------------------------------------------------------------------ sectores
    def _sector(self, clave: str) -> dict | None:
        for nombre in ("interior", "exterior", "apps"):
            for s in self._anillos.get(nombre, []) + anillos.pagina(self._anillos.get(nombre, []), nombre, self._en_mas[nombre]):
                if s["clave"] == clave:
                    return s
        return None

    @Slot(str, result="QVariantMap")
    def sector(self, clave: str) -> dict:
        return self._sector(clave) or {}

    @Slot(str, bool)
    def elegir(self, clave: str, conOpciones: bool) -> None:  # noqa: N803  (nombre para QML)
        """Un sector elegido (clic o archivo soltado encima): «Más»/«Volver» cambian el anillo; uno que pide opciones
        o tiene editor (o con `conOpciones`, el clic derecho) abre el panel; los demás corren ya."""
        if self._proceso_anillos is not None:     # los anillos de lo soltado aún no llegan: se corre al llegar
            self._pendiente = clave
            return
        if clave.startswith(("mas:", "volver:")):            # «Más» y «Volver»: otra página del anillo
            partes = clave.split(":")
            self._en_mas[partes[1]] = max(0, int(partes[2]) if len(partes) > 2 else (1 if partes[0] == "mas" else 0))
            self.cambiada.emit()
            return
        s = self._sector(clave)
        if not s or (not self._archivos and not s.get("sin_archivos")) or self._estado == "corriendo":
            return
        if s["faltan"]:
            self._mensaje = f"«{s['titulo']}» necesita {', '.join(s['faltan'])}, que no está instalado."
            self.cambiada.emit()
            return
        if conOpciones or s["pide"] or s["editor"]:
            self.pedirOpciones.emit(s)
            return
        self.correr(clave, {})

    @Slot(str, "QVariantMap")
    def correr(self, clave: str, valores) -> None:
        s = self._sector(clave)
        if not s or (not self._archivos and not s.get("sin_archivos")) or self._estado == "corriendo":
            return
        params, archivos = self._params(s, valores)
        if s["proveedor"] == "abrir":
            self._abrir_con(s, archivos)
            return
        if s["proveedor"] != "raphi":
            self._correr_orden(s, params, archivos)
            return
        trabajo = self._cache / "trabajos" / f"{int(time.time() * 1000)}.json"
        trabajo.write_text(json.dumps({"operacion": s["operacion"], "archivos": archivos, "params": params,
                                       "destino": None, "simular": False}, ensure_ascii=False), encoding="utf-8")
        self._estado, self._progreso, self._mensaje, self._titulo_trabajo = "corriendo", 0, s["titulo"], s["titulo"]
        self.limpiarVista()
        self.cambiada.emit()
        self._tareas.proceso(f"Raphi: {s['titulo']}", prov_raphi.orden("ejecutar", str(trabajo)),
                             progreso_de=self._progreso_de, operacion="escritura", error=False,
                             al_terminar=lambda codigo, t=trabajo: self._terminado(t, codigo))

    @Slot()
    def abrirPredeterminada(self) -> None:  # noqa: N802
        """Intro sin nada elegido: con la aplicación de siempre (la primera de «Abrir con…»), como el doble clic de antes."""
        primera = next((s for s in self._anillos.get("apps", []) if s.get("predeterminada")), None)
        if primera:
            self.correr(primera["clave"], {})

    def _abrir_con(self, s: dict, archivos: list[str]) -> None:
        try:
            ordenes = abrir.ordenes_para(s["app"], archivos)
        except LookupError as e:
            self._mensaje = str(e)
            self.cambiada.emit()
            return
        fallidas = [o for o in ordenes if not lanzar(o)]
        if fallidas:
            self._mensaje = f"No se pudo abrir con {s['etiqueta']} ({fallidas[0][0]})."
            self.cambiada.emit()
            return
        self._mensaje = f"Abierto con {s['etiqueta']}."
        self.cambiada.emit()
        self.abierto.emit(s["etiqueta"])

    def _correr_orden(self, s: dict, params: dict, archivos: list[str]) -> None:
        """Lo de un studio o del sistema: el proveedor prepara la orden ({argv, cwd, resultado, carpeta, terminal}) y
        se corre como tarea; `resultado` dice qué se mira al terminar (archivos nuevos en `carpeta`, un informe con la
        salida, o nada). `terminal`: se abre en Konsole y no se sigue (ssh, mc, monitores)."""
        modulo = next((m for m in proveedores.LOCALES if getattr(m, "NOMBRE", "") == s["proveedor"]), None)
        if modulo is None or not hasattr(modulo, "preparar"):
            self._mensaje = f"Nadie sabe correr «{s['titulo']}»."
            self.cambiada.emit()
            return
        try:
            plan = modulo.preparar(s, params, archivos)
        except Exception as e:      # noqa: BLE001  un dato que falta, una herramienta que no está
            self._estado, self._mensaje = "error", str(e)
            self.cambiada.emit()
            return
        if plan.get("suelto"):                    # una aplicación que se lanza y no se sigue (Dolphin en smb://, QEMU)
            ok = lanzar(plan["argv"], plan.get("cwd") or "")
            self._mensaje = f"{s['titulo']}: abierto." if ok else f"No se pudo abrir: {plan['argv'][0]}."
            self.cambiada.emit()
            if ok:
                self.abierto.emit(s["titulo"])
            return
        if plan.get("terminal"):
            lanzar(["konsole", "--hold", "-e", *plan["argv"]] if plan.get("mantener") else ["konsole", "-e", *plan["argv"]],
                   plan.get("cwd") or "")
            self._mensaje = f"{s['titulo']}: en Konsole."
            self.cambiada.emit()
            self.abierto.emit(s["titulo"])
            return
        carpeta = Path(plan["carpeta"]) if plan.get("carpeta") else None
        antes = {str(x) for x in carpeta.rglob("*")} if carpeta and carpeta.is_dir() else set()
        salida: list[str] = []
        self._estado, self._progreso, self._mensaje, self._titulo_trabajo = "corriendo", 0, s["titulo"], s["titulo"]
        self.limpiarVista()
        self.cambiada.emit()
        trabajador = self._tareas.proceso(s["titulo"], plan["argv"], cwd=plan.get("cwd"), entorno=plan.get("entorno"),
                                          progreso_de=self._progreso_generico, operacion="escritura", error=False,
                                          al_terminar=lambda codigo: self._orden_terminada(s, plan, carpeta, antes, salida, codigo))
        trabajador.line.connect(lambda texto, _err: salida.append(texto))

    def _progreso_generico(self, linea: str):
        import re
        if linea.startswith("## progreso "):
            return self._progreso_de(linea)
        m = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s?%", linea)
        if m:
            self._progreso = min(100, int(float(m[1].replace(",", "."))))
            self._mensaje = linea.strip()[:120]
            self.cambiada.emit()
            return (self._progreso, self._mensaje)
        return None

    def _orden_terminada(self, s: dict, plan: dict, carpeta, antes: set, salida: list[str], codigo: int) -> None:
        import re
        limpia = [re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", l).rstrip() for l in salida if l.strip()]
        nuevos = sorted(x for x in ({str(y) for y in carpeta.rglob("*")} if carpeta and carpeta.is_dir() else set()) - antes
                        if Path(x).is_file()) if carpeta else []
        nuevos = [x for x in nuevos if not Path(x).name.startswith(".")]
        if codigo != 0:
            self._estado = "error"
            self._mensaje = f"{s['titulo']}: " + (limpia[-1] if limpia else f"terminó con el código {codigo}")
            self._informe = [{"entrada": s["titulo"], "filas": [{"clave": "", "valor": l} for l in limpia[-200:]]}] if limpia else []
        elif plan.get("resultado") == "archivos" and nuevos:
            self._historial.append(self._archivos)
            self._resultados = nuevos[:200]
            self._archivos = list(self._resultados)
            self._estado = "hecha"
            self._mensaje = f"{len(nuevos)} archivos nuevos" if len(nuevos) > 1 else Path(nuevos[0]).name
            self._informe = [{"entrada": s["titulo"], "filas": [{"clave": "", "valor": l} for l in limpia[-200:]]}] if limpia else []
            self._pedir_anillos()
        elif plan.get("resultado") == "informe" or (limpia and plan.get("resultado") != "nada"):
            self._estado = "informe"
            self._mensaje = s["titulo"]
            self._informe = [{"entrada": s["titulo"], "filas": anillos.filas_de_texto(limpia)}]
        else:
            self._estado = "lista"
            self._mensaje = f"{s['titulo']}: hecho." + (f" {limpia[-1]}" if limpia else "")
        self.terminado.emit(codigo == 0, self._mensaje)
        self.cambiada.emit()

    def _params(self, s: dict, valores) -> tuple[dict, list[str]]:
        """Los parámetros de un trabajo: lo que la opción propone (y se puede cambiar), lo escrito en el panel y lo fijo
        de la opción (el formato de destino), en ese orden; con enlaces, van al parámetro que los recibe y no hay archivos."""
        fijos = set(s.get("fijos") or [])
        params = {k: v for k, v in s["params"].items() if k not in fijos}
        params.update({k: v for k, v in dict(valores or {}).items() if v not in ("", None)})
        params.update({k: v for k, v in s["params"].items() if k in fijos})
        if s.get("enlace") and self._son_enlaces():
            params[s["enlace"]] = "\n".join(self._archivos)
            return params, []
        return params, list(self._archivos)

    def _son_enlaces(self) -> bool:
        return bool(self._archivos) and all(anillos.es_enlace(a) for a in self._archivos)

    @Slot()
    def pegar(self) -> None:
        """Ctrl+V: los enlaces o los archivos del portapapeles (un enlace copiado del navegador, archivos copiados en Dolphin)."""
        from gui_comun.qt import QGuiApplication
        datos = QGuiApplication.clipboard().mimeData()
        if datos is None:
            return
        lista = [u.toString() if u.scheme() in ("http", "https") else u.toLocalFile() for u in datos.urls()] if datos.hasUrls() else []
        if not lista and datos.hasText():
            lista = [t for t in datos.text().split() if anillos.es_enlace(t) or Path(t).expanduser().exists()]
        if lista:
            self.cargar(lista)
        else:
            self._mensaje = "El portapapeles no tiene enlaces ni archivos."
            self.cambiada.emit()

    def _progreso_de(self, linea: str):
        if linea.startswith("## progreso "):
            partes = linea[12:].split(" ", 1)
            try:
                self._progreso = int(partes[0])
            except ValueError:
                return None
            if len(partes) > 1 and partes[1].strip():
                self._mensaje = partes[1].strip()
            self.cambiada.emit()
            return (self._progreso, self._mensaje)
        return None

    def _terminado(self, trabajo: Path, codigo: int) -> None:
        informe_ruta = trabajo.with_suffix(".informe.json")
        try:
            informe = json.loads(informe_ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            informe = {"elementos": [], "error": "cancelado" if codigo else "sin informe"}
        for p in (trabajo, informe_ruta):
            p.unlink(missing_ok=True)
        elementos = informe.get("elementos") or []
        salidas = [a for e in elementos for a in (e.get("archivos") or []) if Path(a).exists()]
        errores = [f"{Path(e['entrada']).name}: {e['error']}" if len(elementos) > 1 else e["error"] for e in elementos if e.get("error")]
        avisos = [m for e in elementos for m in (e.get("mensajes") or [])]
        self._informe = [{"entrada": Path(e["entrada"]).name if "/" in e["entrada"] else e["entrada"],
                          "filas": anillos.aplanar(e.get("datos") or {}) + [{"clave": "", "valor": m} for m in e.get("mensajes") or []]}
                         for e in elementos if e.get("ok") and (e.get("datos") or e.get("mensajes"))]
        if not salidas and self._informe:
            self._estado = "informe"
            self._mensaje = f"{self._titulo_trabajo}: " + (f"{len(self._informe)} archivos" if len(self._informe) > 1 else self._informe[0]["entrada"])
            if errores:
                self._mensaje += f" · {len(errores)} con error: {errores[0]}"
            self.terminado.emit(True, self._mensaje)
            self.cambiada.emit()
            return
        if salidas:
            self._historial.append(self._archivos)
            self._resultados = salidas
            self._archivos = list(salidas)
            self._estado = "hecha"
            hechos = f"{len(salidas)} archivos listos" if len(salidas) > 1 else f"{Path(salidas[0]).name}"
            self._mensaje = hechos + (f" · {len(errores)} con error: {errores[0]}" if errores else "")
            self._pedir_anillos()
            self.terminado.emit(True, f"{self._titulo_trabajo}: {hechos}")
        else:
            self._estado = "error" if errores or codigo else "lista"
            self._mensaje = (errores[0] if errores else informe.get("error") or (avisos[0] if avisos else "Sin cambios: no hizo falta escribir nada."))
            if codigo and not errores and not informe.get("error"):
                self._mensaje = "Cancelado."
            self.terminado.emit(False, f"{self._titulo_trabajo}: {self._mensaje}")
        self.cambiada.emit()

    @Slot()
    def cancelar(self) -> None:
        if self._estado == "corriendo":
            self._tareas.cancelar()

    @Slot()
    def deshacer(self) -> None:
        """El último resultado, a la papelera (nunca borrado), y de vuelta al archivo anterior."""
        if self._estado != "hecha" or not self._historial:
            return
        from PySide6.QtCore import QFile
        fallidos = [r for r in self._resultados if Path(r).exists() and not QFile.moveToTrash(r)]
        if fallidos:
            self._mensaje = f"No se pudo mandar a la papelera: {Path(fallidos[0]).name} (sigue donde estaba)."
            self.cambiada.emit()
            return
        self._archivos = self._historial.pop()
        self._resultados = []
        self._mensaje = "El resultado está en la papelera."
        self._estado = "lista"
        self._pedir_anillos()

    @Slot()
    def volver(self) -> None:
        """Al archivo anterior de la cadena, sin borrar nada."""
        if not self._historial or self._estado == "corriendo":
            return
        self._archivos = self._historial.pop()
        self._resultados, self._mensaje, self._estado = [], "", "lista"
        self._pedir_anillos()

    # ------------------------------------------------------------------------------------------------ vista previa
    @Slot(str, result=bool)
    def tieneVista(self, clave: str) -> bool:  # noqa: N802
        """¿Vale la pena la vista previa? En una imagen, siempre; en un PDF, lo que dibuja o reordena (y sus pasos a
        texto o imagen); en un texto, lo que da texto. Comprimir un PDF o pasarle OCR costaría lo que el trabajo."""
        s = self._sector(clave)
        if not s or s.get("proveedor") != "raphi" or not self._archivos or self._son_enlaces() or Path(self._archivos[0]).is_dir():
            return False
        ext = Path(self._archivos[0]).suffix.lower()
        if anillos.es_imagen(self._archivos[0]):
            return True
        if ext == ".pdf":
            return (s.get("categoria") in VISTA_EN_PDF and s["formato"] in ("", "pdf")) or s["formato"] in VISTA_DE_PDF
        return ext in anillos.EXT_TEXTO and (s["formato"] in VISTA_DE_PDF or not s["formato"])

    @Slot(str, "QVariantMap")
    def previsualizar(self, clave: str, valores) -> None:
        """La operación de verdad sobre una copia (reducida, si es una imagen grande) en la caché."""
        s = self._sector(clave)
        if not s or not self.tieneVista(clave):
            self._poner_vista("", "", "sin", "")
            return
        if self._proceso_vista is not None:
            self._proceso_vista.kill()
        self._n_vista += 1
        params = self._params(s, valores)[0]
        trabajo = self._cache / "vistas" / f"t{self._n_vista}.json"
        trabajo.write_text(json.dumps({"operacion": s["operacion"], "archivos": self._archivos[:1], "params": params,
                                       "destino": str(self._cache / "vistas"), "reducir": LADO_VISTA}, ensure_ascii=False),
                           encoding="utf-8")
        self._vista_estado = "cargando"
        self.vistaCambiada.emit()
        proceso = QProcess(self)
        self._proceso_vista = proceso
        proceso.finished.connect(lambda codigo, _e, p=proceso, t=trabajo: self._vista_llego(p, t, codigo))
        orden = prov_raphi.orden("vista", str(trabajo))
        proceso.start(orden[0], orden[1:])

    def _vista_llego(self, proceso: QProcess, trabajo: Path, codigo: int) -> None:
        trabajo.unlink(missing_ok=True)
        if not es_valido(proceso) or not es_valido(self):
            return
        proceso.deleteLater()
        if proceso is not self._proceso_vista:
            return
        self._proceso_vista = None
        salida = bytes(proceso.readAllStandardOutput()).decode("utf-8", "replace").splitlines()
        linea = next((l for l in salida if l.startswith("## vista ")), "")
        if codigo != 0 or not linea:
            # lo que falta (un campo sin llenar, un rectángulo fuera): se ve el original con la nota, no un error en blanco
            error = next((l[7:] for l in salida if l.startswith("raphi: ")), "")
            self._poner_vista("", "", "error", error or "No se pudo generar la vista previa.")
            return
        datos = json.loads(linea[9:])
        if datos.get("archivo") and datos.get("tipo"):
            self._poner_vista(datos["archivo"], datos["tipo"], "lista", "")
        else:
            self._poner_vista("", "", "sin", f"Sin vista para {datos.get('nombre') or 'este resultado'}.")

    def _poner_vista(self, archivo: str, tipo: str, estado: str, nota: str) -> None:
        anterior = self._vista_archivo
        self._vista_archivo, self._vista_tipo, self._vista_estado, self._vista_nota = archivo, tipo, estado, nota
        if anterior and anterior != archivo and Path(anterior).parent == self._cache / "vistas":
            Path(anterior).unlink(missing_ok=True)          # solo la última vista previa queda en la caché
        self._mostrar_vista()

    def _mostrada(self) -> tuple[str, str]:
        """(archivo, tipo) de lo que se ve: el resultado previsto o, con «Ver el original» o sin vista, el original."""
        if self._vista_archivo and not self._ver_original:
            return self._vista_archivo, self._vista_tipo
        original = self._archivos[0] if self._archivos else ""
        return (original, tipo_vista(original)) if original and self._vista_estado in ("error", "lista", "cargando") else ("", "")

    def _mostrar_vista(self) -> None:
        archivo, tipo = self._mostrada()
        if self._visor is not None:
            self._visor.abrir(archivo if tipo == "pdf" else "")
        self.vistaCambiada.emit()

    @Slot(bool)
    def verOriginal(self, si: bool) -> None:  # noqa: N802
        self._ver_original = bool(si)
        self._mostrar_vista()

    @Slot()
    def limpiarVista(self) -> None:  # noqa: N802
        if self._proceso_vista is not None:
            self._proceso_vista.kill()
            self._proceso_vista = None
        self._ver_original = False
        self._poner_vista("", "", "", "")

    @Slot(str)
    def pedirActuales(self, clave: str) -> None:  # noqa: N802
        """Lo que el archivo ya tiene en esa operación (el título y el autor del PDF): llega por `valoresActuales`."""
        s = self._sector(clave)
        if not s or not s.get("con_actuales") or len(self._archivos) != 1:
            return
        proceso = QProcess(self)

        def llego(codigo, _e, p=proceso, c=clave):
            if not es_valido(p) or not es_valido(self):
                return
            p.deleteLater()
            try:
                valores = json.loads(bytes(p.readAllStandardOutput()).decode("utf-8")) if codigo == 0 else {}
            except ValueError:
                valores = {}
            if valores:
                self.valoresActuales.emit(c, valores)
        proceso.finished.connect(llego)
        orden = prov_raphi.orden("actuales", s["operacion"], self._archivos[0])
        proceso.start(orden[0], orden[1:])

    # ------------------------------------------------------------------------------------------------ utilidades
    @Slot(str, result=str)
    def url(self, ruta: str) -> str:
        return QUrl.fromLocalFile(ruta).toString() if ruta else ""

    @Slot(str, result=str)
    def nombre(self, ruta: str) -> str:
        return Path(ruta).name

    # ------------------------------------------------------------------------------------------------ Okular y compartir
    @Slot()
    def refrescarOkular(self) -> None:  # noqa: N802
        """Lo que Okular muestra ahora (al aparecer la rueda): para tomar de ahí el documento y la página."""
        self._okular = documentos_okular()
        self.cambiada.emit()

    @Slot(str)
    def abrirEnOkular(self, ruta: str) -> None:  # noqa: N802
        """En el Okular abierto (como pestaña nueva si así lo tiene configurado) o en uno nuevo."""
        lanzar(["okular", "--unique", ruta] if self._okular else ["okular", ruta])

    @Slot()
    def enviarPorCorreo(self) -> None:  # noqa: N802
        """El resultado (o lo del centro) como adjunto de un correo nuevo, en el programa de correo de la sesión."""
        archivos = [a for a in (self._resultados or self._archivos) if Path(a).is_file()]
        if not archivos:
            return
        orden = [x for a in archivos for x in ("--attach", a)] + ["--subject", ", ".join(Path(a).name for a in archivos)[:120]]
        if not lanzar(["xdg-email", *orden]):
            self._mensaje = "No se pudo abrir el programa de correo (xdg-email)."
            self.cambiada.emit()

    @Slot()
    def copiarArchivos(self) -> None:  # noqa: N802
        """El resultado al portapapeles como archivos: se pega en Dolphin, en el escritorio o en un chat."""
        from gui_comun.qt import QGuiApplication
        from PySide6.QtCore import QMimeData
        archivos = [a for a in (self._resultados or self._archivos) if not anillos.es_enlace(a)]
        if not archivos:
            return
        datos = QMimeData()
        datos.setUrls([QUrl.fromLocalFile(a) for a in archivos])
        datos.setData("x-special/gnome-copied-files", ("copy\n" + "\n".join(QUrl.fromLocalFile(a).toString() for a in archivos)).encode())
        QGuiApplication.clipboard().setMimeData(datos)
        self._mensaje = f"Copiado: pégalo en Dolphin o en un chat ({len(archivos)} archivo{'s' if len(archivos) > 1 else ''})."
        self.cambiada.emit()

    @Slot(bool)
    def fijarVisible(self, si: bool) -> None:  # noqa: N802
        self._visible = si

    def avisar(self, ok: bool, mensaje: str) -> None:
        """Si la rueda ya no se ve cuando el trabajo acaba, el aviso va a las notificaciones de KDE."""
        if not self._visible and self._notificador is not None:
            self._notificador.notificar(mensaje, "informacion" if ok else "error")

    # ------------------------------------------------------------------------------------------------ propiedades
    @Property("QVariantList", notify=cambiada)
    def archivos(self):
        return self._archivos

    @Property(int, notify=cambiada)
    def cuantos(self) -> int:
        return len(self._archivos)

    @Property(str, notify=cambiada)
    def primera(self) -> str:
        return self._archivos[0] if self._archivos else ""

    @Property(bool, notify=cambiada)
    def primeraEsImagen(self) -> bool:  # noqa: N802
        return bool(self._archivos) and not self._son_enlaces() and anillos.es_imagen(self._archivos[0]) and not Path(self._archivos[0]).suffix.lower() in (".heic", ".heif", ".avif")

    @Property(str, notify=cambiada)
    def icono(self) -> str:
        """El icono del tipo de lo que hay en el centro."""
        if not self._archivos:
            return "document-import"
        if self._son_enlaces():
            return "download"
        if Path(self._archivos[0]).is_dir():
            return "folder"
        return anillos.icono_formato(Path(self._archivos[0]).suffix.lstrip("."))

    @Property(str, notify=cambiada)
    def texto(self) -> str:
        if not self._archivos:
            return "Suelta aquí"
        if self._son_enlaces():
            from urllib.parse import urlparse
            u = urlparse(self._archivos[0])
            return f"{len(self._archivos)} enlaces" if len(self._archivos) > 1 else (u.netloc.removeprefix("www.") + u.path)[:60]
        if len(self._archivos) > 1:
            return f"{len(self._archivos)} archivos"
        return Path(self._archivos[0]).name

    @Property("QVariantList", notify=cambiada)
    def interior(self):
        return anillos.pagina(self._anillos["interior"], "interior", self._en_mas["interior"])

    @Property("QVariantList", notify=cambiada)
    def apps(self):
        return anillos.pagina(self._anillos["apps"], "apps", self._en_mas["apps"])

    @Property(str, notify=cambiada)
    def predeterminada(self) -> str:
        """El nombre de la aplicación de siempre para lo del centro (lo que abre Intro)."""
        return next((s["etiqueta"] for s in self._anillos.get("apps", []) if s.get("predeterminada")), "")

    @Property("QVariantList", notify=cambiada)
    def exterior(self):
        return anillos.pagina(self._anillos["exterior"], "exterior", self._en_mas["exterior"])

    @Property(str, notify=cambiada)
    def estado(self) -> str:
        return self._estado

    @Property(int, notify=cambiada)
    def progreso(self) -> int:
        return self._progreso

    @Property(str, notify=cambiada)
    def mensaje(self) -> str:
        return self._mensaje

    @Property("QVariantList", notify=cambiada)
    def resultados(self):
        return self._resultados

    @Property(str, notify=cambiada)
    def uriList(self) -> str:  # noqa: N802
        """Lo que se arrastra fuera (text/uri-list): el resultado, o lo que haya en el centro."""
        return "\r\n".join(r if anillos.es_enlace(r) else QUrl.fromLocalFile(r).toString() for r in (self._resultados or self._archivos)) + "\r\n"

    @Property("QVariantList", notify=cambiada)
    def okular(self):
        return self._okular

    @Property(int, notify=cambiada)
    def paginaOkular(self) -> int:  # noqa: N802
        """La página que Okular muestra del archivo del centro (0 si Okular no lo tiene abierto)."""
        actual = self._archivos[0] if len(self._archivos) == 1 else ""
        return next((d["pagina"] for d in self._okular if d["ruta"] == actual), 0)

    @Property(bool, notify=cambiada)
    def sonEnlaces(self) -> bool:  # noqa: N802
        return self._son_enlaces()

    @Property(bool, notify=cambiada)
    def hayHistorial(self) -> bool:  # noqa: N802
        return bool(self._historial)

    @Property(str, notify=cambiada)
    def cadena(self) -> str:
        """De dónde viene lo del centro: «informe.pdf › informe.jpg › informe_recortada.jpg»."""
        pasos = [h[0] if len(h) == 1 else f"{len(h)} archivos" for h in self._historial] + ([self._archivos[0] if len(self._archivos) == 1 else f"{len(self._archivos)} archivos"] if self._archivos else [])
        return " › ".join(p if anillos.es_enlace(p) else Path(p).name if "/" in p else p for p in pasos[-4:])

    visorPdf = Property(QObject, lambda self: self._visor, constant=True)

    @Property(str, notify=vistaCambiada)
    def vistaEstado(self) -> str:  # noqa: N802
        return self._vista_estado

    @Property(str, notify=vistaCambiada)
    def vistaNota(self) -> str:  # noqa: N802
        return self._vista_nota

    @Property(str, notify=vistaCambiada)
    def vistaTipo(self) -> str:  # noqa: N802
        return self._mostrada()[1]

    @Property(str, notify=vistaCambiada)
    def vistaUrl(self) -> str:  # noqa: N802
        archivo, tipo = self._mostrada()
        return QUrl.fromLocalFile(archivo).toString() + f"?v={self._n_vista}" if archivo and tipo == "imagen" else ""

    @Property(str, notify=vistaCambiada)
    def vistaContenido(self) -> str:  # noqa: N802
        archivo, tipo = self._mostrada()
        if tipo != "texto":
            return ""
        try:
            return Path(archivo).read_text(encoding="utf-8", errors="replace")[:400_000]
        except OSError:
            return ""

    @Property(bool, notify=vistaCambiada)
    def viendoOriginal(self) -> bool:  # noqa: N802
        return bool(self._mostrada()[0]) and self._mostrada()[0] == (self._archivos[0] if self._archivos else "")

    @Property(bool, constant=True)
    def cerrarIzquierda(self) -> bool:  # noqa: N802
        return self._cerrar_izquierda

    @Property("QVariantList", notify=cambiada)
    def informe(self):
        return self._informe

    @Slot()
    def copiarInforme(self) -> None:  # noqa: N802
        from gui_comun.qt import QGuiApplication
        texto = "\n\n".join(f"{b['entrada']}\n" + "\n".join(f"{f['clave']}: {f['valor']}" for f in b["filas"]) for b in self._informe)
        QGuiApplication.clipboard().setText(texto)

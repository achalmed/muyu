"""muyu/anillos.py — qué va en cada anillo de la rueda, sin Qt (se prueba solo).

La rueda no nombra operaciones: recibe de los proveedores (`muyu/proveedores/`: el corredor de Raphi, «Abrir con…»,
los studios, el sistema) lo que ofrecen para los archivos con la ficha de cada opción, y lo reparte:

- **anillo interior, «Convertir a»**: las opciones con formato de destino (DOCX, JPG, MP3…);
- **anillo exterior, «Herramientas»**: las que transforman o hacen algo sin cambiar de formato;
- **anillo de afuera, «Abrir con…»**: las aplicaciones del sistema, la de siempre primero (`anillo: "apps"`).

Cada anillo muestra hasta `TOPE` sectores; si hay más, el último es «Más», que abre el resto en el mismo anillo con un
sector «Volver». Cada sector dice si pide opciones antes de correr (`pide`: un texto vacío por llenar o una clave) y
qué editor a la vista tiene (`editor`: la pista `vista` de un parámetro, p. ej. «caja», el recorte).
"""
from __future__ import annotations

import json
from pathlib import Path

TOPE = {"interior": 8, "exterior": 10, "apps": 12}
COLA_GENERICA = {"imagen", "pdf", "video", "vídeo", "audio", "o", "dos"}   # «Comprimir PDF» → «Comprimir»: el centro ya dice el tipo
ICONO_FORMATO = {
    "pdf": "application-pdf", "pdf/a": "application-pdf", "docx": "x-office-document", "odt": "x-office-document",
    "doc": "x-office-document", "rtf": "x-office-document", "txt": "text-plain", "md": "text-markdown", "html": "text-html",
    "xlsx": "x-office-spreadsheet", "ods": "x-office-spreadsheet", "pptx": "x-office-presentation", "odp": "x-office-presentation",
    "zip": "application-zip", "srt": "media-subtitle", "vtt": "media-subtitle",
}
IMAGENES = {"jpg", "jpeg", "png", "webp", "avif", "heic", "tiff", "bmp", "gif", "svg"}
AUDIO = {"mp3", "m4a", "flac", "opus", "ogg", "wav", "aac"}
VIDEO = {"mp4", "mov", "mkv", "webm", "avi", "m4v"}
EXT_IMAGEN = {"." + e for e in IMAGENES} | {".heif", ".tif"}
EXT_TEXTO = {".txt", ".md", ".srt", ".vtt", ".csv", ".tsv", ".json", ".html", ".htm", ".tex", ".log"}
PIDEN = ("texto", "multilinea", "clave")
# El orden del anillo interior: los destinos más pedidos primero (los demás, en el orden del motor, detrás o en «Más»)
PRIMEROS = ("pdf", "docx", "jpg", "png", "txt", "md", "webp", "mp4", "mp3", "xlsx", "odt", "html", "zip")


def icono_formato(formato: str) -> str:
    f = (formato or "").lower()
    if f in ICONO_FORMATO:
        return ICONO_FORMATO[f]
    if f in IMAGENES:
        return "image-" + ("jpeg" if f == "jpg" else f)
    if f in AUDIO:
        return "audio-x-generic"
    if f in VIDEO:
        return "video-x-generic"
    return "unknown"


def etiqueta_corta(titulo: str) -> str:
    """El título sin paréntesis ni la cola que repite el tipo: «Comprimir PDF» → «Comprimir»."""
    palabras = titulo.split(" (")[0].split()
    while len(palabras) > 1 and palabras[-1].lower() in COLA_GENERICA:
        palabras.pop()
    return " ".join(palabras)


def pide_opciones(parametros: list[dict]) -> bool:
    """¿Hay que preguntar antes de correr? Si algún parámetro es obligatorio o es un texto, una clave o un texto largo
    sin valor por omisión (tachar sin términos, cifrar sin contraseña, una nota sin texto: no harían nada útil), o si
    hay un color que elegir (poner fondo, foliar, un sello: se elige mirando la vista previa)."""
    return any(p.get("obligatorio") or p.get("tipo") == "color" or (p.get("tipo") in PIDEN and p.get("defecto") in (None, ""))
               for p in parametros)


def orden_formato(sector: dict) -> int:
    f = sector["formato"].lower()
    return PRIMEROS.index(f) if f in PRIMEROS else len(PRIMEROS)


def editor_de(parametros: list[dict]) -> tuple[str, str]:
    """(vista, clave) del parámetro con un editor a la vista, o ("", "")."""
    return next(((p["vista"], p["clave"]) for p in parametros if p.get("vista")), ("", ""))


def clave_de(opcion: dict) -> str:
    return opcion["operacion"] + "|" + json.dumps(opcion.get("params") or {}, sort_keys=True, ensure_ascii=False)


def campos_formulario(f: dict) -> list[dict]:
    """Los campos de `PaginaFormulario` (gui-comun) desde los parámetros de una ficha: los tipos que el marco no tiene
    se traducen (paginas y tamano a texto con su marcador; json a multilínea)."""
    salida = []
    for p in f.get("parametros", []):
        tipo, marcador = p["tipo"], ""
        if tipo == "paginas":
            tipo, marcador = "texto", "todas · 1-3,5 · último"
        elif tipo == "tamano":
            tipo, marcador = "texto", "p. ej. 10 MB"
        elif tipo == "json":
            tipo, marcador = "multilinea", "JSON"
        salida.append({"clave": p["clave"], "etiqueta": p["etiqueta"], "tipo": tipo, "defecto": p.get("defecto"),
                       "opciones": p.get("opciones") or [], "minimo": p.get("minimo"), "maximo": p.get("maximo"),
                       "ayuda": p.get("ayuda") or "", "obligatorio": bool(p.get("obligatorio")), "marcador": marcador})
    return salida


def sector(opcion: dict, icono_operacion=None) -> dict:
    """Un sector de la rueda desde una opción del corredor. `icono_operacion(ficha)` da el icono de una herramienta.

    La opción puede traer lo suyo (las de un enlace lo traen): `etiqueta`, `icono`, `clave`, `pide`, `fijos` (qué
    parámetros no se preguntan; por omisión, los que fija la opción) y `enlace` (el parámetro que recibe los enlaces)."""
    formato = opcion.get("a")
    parametros = opcion.get("parametros") or []
    params = opcion.get("params") or {}
    titulo = opcion["titulo"]
    propia = bool(opcion.get("etiqueta"))
    enlace = opcion.get("enlace") or ""
    fijos = sorted(set(opcion["fijos"] if "fijos" in opcion else params) | ({enlace} if enlace else set()))
    return {
        "clave": opcion.get("clave") or clave_de(opcion), "operacion": opcion["operacion"], "params": params,
        "etiqueta": opcion.get("etiqueta") or (formato.upper() if formato else etiqueta_corta(titulo)),
        "titulo": titulo if propia or not formato else f"A {formato.upper()} · {titulo}", "descripcion": opcion.get("descripcion", ""),
        "categoria": opcion.get("categoria", ""),
        "icono": opcion.get("icono") or (icono_formato(formato) if formato else (icono_operacion(opcion) if icono_operacion else "application-x-executable")),
        "proveedor": opcion.get("proveedor", "raphi"), "anillo": opcion.get("anillo", ""), "app": opcion.get("app", ""),
        "predeterminada": bool(opcion.get("predeterminada")), "resultado": opcion.get("resultado", ""),
        "formato": formato or "", "junta": bool(opcion.get("junta")), "faltan": list(opcion.get("faltan") or []),
        "campos": campos_formulario({"parametros": parametros}), "fijos": fijos, "enlace": enlace,
        "pide": opcion["pide"] if "pide" in opcion else pide_opciones([p for p in parametros if p["clave"] not in fijos]),
        "editor": editor_de(parametros)[0], "editor_clave": editor_de(parametros)[1], "mas": False,
        "con_actuales": bool(opcion.get("con_actuales")), "sin_archivos": bool(opcion.get("sin_archivos")),
        "grupo": opcion.get("grupo", ""),
    }


def _especial(clave: str, etiqueta: str, titulo: str, descripcion: str, icono: str, anillo: str) -> dict:
    return {"clave": clave, "operacion": "", "params": {}, "etiqueta": etiqueta, "titulo": titulo, "categoria": "",
            "descripcion": descripcion, "icono": icono, "formato": "", "junta": False, "faltan": [], "campos": [], "fijos": [],
            "pide": False, "editor": "", "editor_clave": "", "mas": True, "proveedor": "", "anillo": anillo if anillo == "apps" else "",
            "app": "", "predeterminada": False, "resultado": "", "enlace": "", "con_actuales": False, "sin_archivos": True, "grupo": ""}


def pagina(sectores: list[dict], anillo: str, n: int = 0) -> list[dict]:
    """Lo que se ve de un anillo en su página `n`: si no cabe, la primera trae «Más»; las siguientes, su tanda con
    «Más» (si queda) y «Volver». Así un anillo nunca tiene más de `TOPE` sectores, haya las herramientas que haya."""
    tope = TOPE[anillo]
    if len(sectores) <= tope:
        return list(sectores)
    primera, por_pagina = tope - 1, tope - 2
    if n <= 0:
        resto = len(sectores) - primera
        return list(sectores[:primera]) + [_especial(f"mas:{anillo}:1", f"Más ({resto})", "Más opciones",
                                                      ", ".join(x["etiqueta"] for x in sectores[primera:primera + 6]) + ("…" if resto > 6 else ""),
                                                      "view-more-symbolic", anillo)]
    inicio = primera + (n - 1) * por_pagina
    trozo = list(sectores[inicio:inicio + por_pagina])
    resto = len(sectores) - (inicio + por_pagina)
    if resto > 0:
        trozo.append(_especial(f"mas:{anillo}:{n + 1}", f"Más ({resto})", "Más opciones",
                               ", ".join(x["etiqueta"] for x in sectores[inicio + por_pagina:inicio + por_pagina + 6]), "view-more-symbolic", anillo))
    trozo.append(_especial(f"volver:{anillo}:{n - 1}", "Volver", "Volver", "La página anterior", "go-previous-symbolic", anillo))
    return trozo


def construir(opciones: list[dict], icono_operacion=None) -> dict:
    """{interior, exterior, apps}: todos los sectores de cada anillo (`pagina` dice cuáles se ven)."""
    sectores = [sector(o, icono_operacion) for o in opciones]
    apps = [s for s in sectores if s["anillo"] == "apps"]
    resto = [s for s in sectores if s["anillo"] != "apps"]
    # al interior van los formatos de destino y lo que pida ir ahí (las generales de los studios en la rueda vacía)
    interior = sorted((s for s in resto if s["formato"] or s["anillo"] == "interior"), key=orden_formato)    # estable
    exterior = [s for s in resto if not s["formato"] and s["anillo"] != "interior"]
    return {"interior": interior, "exterior": exterior, "apps": apps}


def es_enlace(texto: str) -> bool:
    return texto.startswith(("http://", "https://"))


def clave_cache(rutas: list[str]) -> str:
    """Lo que la rueda ofrece depende solo de las extensiones y de si es uno o varios (`opciones_para`): la clave de
    la caché. Una carpeta cuenta como «/»; los enlaces, como «enlaces»."""
    if rutas and all(es_enlace(r) for r in rutas):
        return ("varios:" if len(rutas) > 1 else "uno:") + "enlaces"
    exts = sorted({("/" if Path(r).is_dir() else Path(r).suffix.lower()) for r in rutas})
    return ("varios:" if len(rutas) > 1 else "uno:") + ",".join(exts)


def es_imagen(ruta: str) -> bool:
    return Path(ruta).suffix.lower() in EXT_IMAGEN


def aplanar(datos, prefijo: str = "", tope: int = 400) -> list[dict]:
    """Los datos de un informe del motor (diccionarios y listas anidados) como filas {clave, valor} para leerlas:
    «autor: Ana», «paginas › 1 › ancho: 595». Una lista de valores simples va en una sola fila; se corta en `tope`."""
    filas: list[dict] = []

    def poner(clave: str, valor) -> None:
        if len(filas) >= tope:
            return
        if isinstance(valor, dict):
            for k, v in valor.items():
                poner(f"{clave} › {k}" if clave else str(k), v)
        elif isinstance(valor, (list, tuple)) and any(isinstance(v, (dict, list, tuple)) for v in valor):
            for i, v in enumerate(valor, 1):
                poner(f"{clave} › {i}" if clave else str(i), v)
        elif isinstance(valor, (list, tuple)):
            filas.append({"clave": clave, "valor": ", ".join(str(v) for v in valor)})
        else:
            filas.append({"clave": clave, "valor": "sí" if valor is True else "no" if valor is False else str(valor)})
    poner(prefijo, datos)
    return filas


def filas_de_texto(lineas: list[str], tope: int = 400) -> list[dict]:
    """La salida de una orden como filas de informe: «clave: valor» si la línea lo parece, si no la línea entera."""
    import re
    filas = []
    for linea in lineas[-tope:]:
        m = re.match(r"^\s*([^:]{1,40}?)\s*[:=]\s+(.+)$", linea)
        filas.append({"clave": m[1], "valor": m[2]} if m and not linea.lstrip().startswith(("http", "/")) else {"clave": "", "valor": linea})
    return filas

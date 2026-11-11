"""Los proveedores de la rueda: cada uno dice qué ofrece para unas rutas (o enlaces) y cómo se corre.

- `raphi`: el motor de Raphi, por su corredor (en otro proceso, con su `.venv`; la ventana lo pide aparte y lo guarda
  en caché por extensiones);
- `abrir`: «Abrir con…», las aplicaciones del sistema (en este proceso);
- `studios`: las herramientas de Filesystem, Git, LaTeX, Quarto y Huella Studio, por su CLI;
- `sistema`: lo de KDE-Services fuera del dominio de Raphi (red, ISO, seguridad, Android, copias, búsquedas, sistema).

Cada opción lleva `proveedor`; la ventana elige con él cómo correrla. `locales(rutas)` junta las que se calculan aquí.
"""
from __future__ import annotations

from muyu.proveedores import abrir, raphi, sistema, studios  # noqa: F401

LOCALES = [studios, sistema, abrir]


def registrar(modulo) -> None:
    """Un proveedor que se calcula en este proceso (`opciones(rutas) -> list[dict]`)."""
    if modulo not in LOCALES:
        LOCALES.append(modulo)


def locales(rutas: list[str]) -> list[dict]:
    salida: list[dict] = []
    for modulo in LOCALES:
        try:
            salida += modulo.opciones(list(rutas))
        except Exception as e:      # noqa: BLE001  un proveedor roto no deja la rueda vacía
            salida.append({"proveedor": "error", "operacion": f"error:{modulo.__name__}", "clave": f"error|{modulo.__name__}",
                           "a": None, "etiqueta": "Error", "titulo": f"{modulo.__name__}: {e}", "descripcion": str(e),
                           "icono": "dialog-error", "params": {}, "parametros": [], "pide": False, "faltan": [str(e)]})
    return salida

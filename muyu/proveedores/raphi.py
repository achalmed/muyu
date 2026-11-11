"""El proveedor Raphi: documentos, PDF, imágenes, audio, vídeo, metadatos, sumas y descargas, por el corredor del motor
de Raphi (`raphi/escritorio/studio/corredor.py`), que es su API de proceso: `rueda <rutas o enlaces…>` dice qué ofrece
con la ficha de cada opción, `ejecutar`, `vista` y `actuales` lo corren. Muyu no importa nada de Raphi.

Lo que ofrece depende solo de las extensiones (y de si son enlaces), así que la ventana lo guarda en caché.
"""
from __future__ import annotations

from muyu import rutas

NOMBRE = "raphi"


def disponible() -> bool:
    return rutas.hay_raphi()


def orden(pedido: str, *args: str) -> list[str]:
    """La orden del corredor: `orden("rueda", *rutas)`, `orden("ejecutar", trabajo.json)`, `orden("vista", …)`."""
    return [rutas.raphi_python(), str(rutas.raphi_corredor()), pedido, *args]


def marcar(opciones: list[dict]) -> list[dict]:
    """Las opciones del corredor, con su proveedor."""
    return [{**o, "proveedor": NOMBRE} for o in opciones]

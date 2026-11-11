"""`python3 -m escritorio [--residente] [archivos o enlaces…]` (o `muyu`, `run.sh`): la rueda de Muyu.

Si ya hay una abierta (la residente), le pasa los archivos y sale enseguida, sin cargar Qt: así el doble clic es
inmediato. Corre con el Python del sistema (/usr/bin/python3), el que trae Kirigami y layer-shell.

    muyu informe.pdf foto.jpg            # la rueda con esos archivos en el centro (el doble clic, Dolphin, Krusader)
    muyu "https://youtu.be/…"            # la rueda de descargas de un enlace
    muyu                                 # vacía, bajo el puntero: el atajo global, en medio de un arrastre
    muyu --residente                     # se queda con la franja del borde de la pantalla (inicio con la sesión)
    muyu --instalar [--residente] [--predeterminada] [-n]   # acceso, atajo, menús, inicio, macro, predeterminada
    muyu --quitar [-n]                   # lo quita todo y devuelve las aplicaciones predeterminadas de antes
    muyu --opciones archivo…             # lo que la rueda ofrecería (de los proveedores de este proceso), en texto
    muyu --smoke · --captura salida.png [archivos…]   # pruebas
"""
import sys
from pathlib import Path


def _ordenes(argv: list[str]) -> int | None:
    from muyu import instalar
    simular = "-n" in argv or "--simular" in argv
    if "--instalar" in argv:
        lineas = instalar.instalar(residente="--residente" in argv, predeterminada="--predeterminada" in argv, simular=simular)
    elif "--quitar" in argv:
        lineas = instalar.quitar(simular)
    elif "--opciones" in argv:
        from muyu import proveedores
        rutas_ = [a if a.startswith(("http://", "https://")) else str(Path(a).resolve()) for a in argv if not a.startswith("-")]
        for o in proveedores.locales(rutas_):
            print(f"{o.get('proveedor', ''):>8} · {o.get('etiqueta', '')}: {o.get('titulo', '')}")
        return 0
    else:
        return None
    for linea in lineas:
        print(("· " if simular else "✓ ") + linea)
    if simular:
        print("(simulado: nada escrito; sin -n, se escribe)")
    return 0


def main(argv: list[str]) -> int:
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    hecho = _ordenes(argv)
    if hecho is not None:
        return hecho
    from escritorio.aplicacion import mandar_a_la_abierta
    pruebas = "--smoke" in argv or "--captura" in argv
    archivos = [a if a.startswith(("http://", "https://")) else str(Path(a).resolve()) for i, a in enumerate(argv)
                if not a.startswith("-") and (i == 0 or argv[i - 1] != "--captura")]
    # con otra abierta: le pasa los archivos y que se muestre; un «--residente» (el inicio de sesión) sale callado
    if not pruebas and mandar_a_la_abierta(archivos, "--residente" not in argv or bool(archivos)):
        return 0
    from escritorio.aplicacion import main as rueda
    return rueda(argv)


sys.exit(main(sys.argv[1:]))

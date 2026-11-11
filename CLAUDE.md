---
tipo: guia_ia
estado: activo
---
# CLAUDE.md — muyu

Guía para el asistente. Rige la del raíz (`~/Documents/CLAUDE.md`); aquí solo lo propio. `AGENTS.md` es un enlace a
este archivo. Léase antes: `estado.md`, `README.md` y `docs/decisiones.md`.

## Reglas que no se negocian

- **Muyu no hace lo que otro proyecto ya hace**: lo pide por la CLI de ese proyecto (su `suite.yml`), nunca
  importando su código (`tests/test_nucleo.py` lo vigila). Lo de documentos y medios es de **Raphi**, por su corredor
  (`rueda`, `ejecutar`, `vista`, `actuales`): una operación nueva va al motor de Raphi, no aquí.
- **Un proveedor** (`muyu/proveedores/`) es un módulo con `NOMBRE`, `opciones(rutas) -> list[dict]` y, si corre
  órdenes, `preparar(sector, params, archivos) -> {argv, cwd, resultado, carpeta, terminal, mantener, suelto}`. La
  ventana no nombra operaciones: solo reparte lo que llega (`muyu/anillos.py`).
- **Cada proyecto por el manifiesto** (`muyu/rutas.py`: `meta/workspace.yml`), nunca una ruta de la máquina escrita.
- **Lo que destruye o renombra pide confirmarlo** (el campo `confirmo`); lo que necesita root o es interactivo se
  abre en Konsole (la contraseña, la escribe la persona); nada de `sudo` sin terminal.
- **La predeterminada se devuelve**: `instalar.predeterminar` respalda `mimeapps.list` y guarda la aplicación de cada
  tipo; `quitar` la restituye. Nunca se toman carpetas, `x-scheme-handler/*`, ejecutables ni `.desktop`.
- **El repo es público** (desde el 2026-11-11, M2; AGPL-3.0): nada del despacho ni de nadie, ninguna ruta de la
  máquina; `python3 scripts/escanear.py` (y la guarda pre-push que instala `--instalar-guarda`) escanea cada envío. Las
  capturas van a `docs/capturas/` (las únicas que deja salir `demo/demo.conf`), hechas con archivos de ejemplo.
- **Huella es sensible** (regla 8 de la guía raíz): Muyu corre sus fases y muestra su salida en la ventana; nunca la
  copia a un archivo, a las pruebas ni a las capturas.
- **Sin colores propios en QML** y la ventana con el Python del sistema (`run.sh`).

## Cómo se verifica un cambio

```bash
tests/run.sh                                               # en proceso y la ventana sin pantalla
python3 scripts/escanear.py --trabajo                      # la guarda del repo público
./run.sh --opciones <archivo o carpeta>                    # lo que ofrecería
QT_QPA_PLATFORM=offscreen MUYU_ESPERA=4000 ./run.sh --captura /tmp/x.png <archivo>   # cómo se ve
./run.sh --instalar --residente --predeterminada -n        # lo que pondría en KDE
```

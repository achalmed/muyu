---
tipo: readme
estado: activo
---
# muyu/ — Muyu, la rueda universal del escritorio: abrir con, convertir y las herramientas de tus programas

<!-- suite:inicio -->
**Suite `muyu`** · objetivo *sistema* · estado *activo* · python · interfaz gui

La rueda universal del escritorio: abrir con, convertir y las herramientas de Raphi, de los studios y del sistema sobre cualquier archivo, carpeta o enlace.

- Escribe en: archivos · simula por defecto: no
- Depende de: python3-pyside6 (sistema) con Kirigami y layer-shell-qt, gui-comun, raphi (su corredor y su .venv)

Comandos:

```bash
main.py [archivos o enlaces]
run.sh --residente
run.sh --instalar --residente --predeterminada -n
run.sh --quitar
```

<sub>Bloque generado desde `suite.yml` por `core/suites.py generar` (2026-11-11); no se edita a mano.</sub>
<!-- suite:fin -->

<!-- suites:inicio -->
Suites de esta carpeta (1); índice global en `meta/INDICE_SCRIPTS.md`. Patrón: M main · C config · L lib.

| Suite | Carpeta | Objetivo | Escribe en | Simula | Timer | Estado | Patrón |
|---|---|---|---|---|---|---|---|
| `muyu` | [muyu](./) | sistema | archivos | no |  | activo | `M··` |

<sub>Bloque generado desde los `suite.yml` por `core/suites.py generar` (2026-11-11); no se edita a mano.</sub>
<!-- suites:fin -->

## Qué es

**Muyu** («círculo, giro» en quechua) es la rueda universal del escritorio: suelta un archivo, una carpeta o un enlace
—o haz doble clic en un archivo, porque Muyu es la aplicación predeterminada— y aparece un círculo bajo el puntero
con todo lo que se puede hacer con eso en esta máquina:

- **afuera, «Abrir con…»**: las aplicaciones que el sistema conoce para ese tipo; la de siempre va primero y la abre
  **Intro** (el doble clic de antes, a una tecla);
- **interior, «Convertir a»**: los formatos de destino (Raphi: PDF, DOCX, JPG, MP3, SRT…);
- **exterior, «Herramientas»**: lo de Raphi (comprimir, OCR, tachar, metadatos, recortar, poner fondo, descargar,
  transcribir…), lo de tus studios (Filesystem, Git, LaTeX, Quarto, Huella) y lo de sistema que traía KDE-Services
  (red, ISO, seguridad, Android, copias, búsquedas, sistema), página a página con «Más».

El resultado queda en el centro: se arrastra fuera o se sigue trabajando con él. Con la rueda vacía (el atajo
Meta+Ctrl+R) están las herramientas generales: Huella por fases, el estado de los repos, los blogs, SSH, Samba,
Android, información del sistema.

## Uso

```bash
./run.sh archivo.pdf foto.jpg                          # la rueda con esos archivos en el centro
./run.sh "https://youtu.be/…"                          # la rueda de descargas de un enlace
./run.sh                                               # vacía, bajo el puntero (lo que hace el atajo Meta+Ctrl+R)
./run.sh --residente                                   # se queda con la franja del borde derecho (inicio con la sesión)
./run.sh --instalar --residente --predeterminada -n    # qué pondría en KDE; sin -n, lo pone (respalda mimeapps.list)
./run.sh --quitar                                      # lo quita y devuelve a cada tipo su aplicación de antes
./run.sh --opciones carpeta/                           # lo que ofrecerían los proveedores de este proceso, en texto
tests/run.sh                                           # las pruebas (en proceso y la ventana sin pantalla)
```

En la rueda: clic o soltar encima corre; clic derecho abre las opciones (con vista previa en vivo); ← → recorren;
Intro abre con la de siempre o corre lo elegido; Ctrl+V pega un enlace o archivos; Retroceso vuelve; Ctrl+Z deshace;
Esc cierra.

## Estructura

| carpeta | qué es |
|---|---|
| `muyu/` | el paquete sin Qt: `rutas.py` (cada proyecto por `meta/workspace.yml`), `anillos.py` (qué va en cada anillo y sus páginas), `instalar.py` (KDE, la predeterminada y su vuelta), `proveedores/` |
| `muyu/proveedores/` | `raphi` (el motor de Raphi por su corredor), `abrir` («Abrir con…»), `studios` (las CLI de Filesystem, Git, LaTeX, Quarto y Huella), `sistema` (lo de KDE-Services) |
| `escritorio/` | la ventana: `aplicacion.py` (instancia única, layer-shell), `controlador.py` (`Rueda`), `qml/` |
| `tests/` | las pruebas (`tests/run.sh`) |

Muyu no hace por sí mismo lo que otro proyecto ya hace: lo pide por la CLI de ese proyecto (el contrato de su
`suite.yml`), nunca importando su código. Corre con el Python del sistema (PySide6 con Kirigami y layer-shell).

## Lo que necesita

PySide6 y Kirigami del sistema, `gui-comun` (al lado o instalado) y, para lo de cada proveedor, sus programas: Raphi
con su `.venv` al lado; `gpg`, `sshfs`, `adb`, `xorriso`, `qemu-system-x86`, `gocryptfs`, `plocate`, `fastfetch`…
Lo que falta lo dice la rueda en el sector. Lo que no trae Ubuntu de base:

```bash
sudo apt install isomd5sum wodim mc inxi cifs-utils rpm
```

## Límite honesto

- **Wayland no deja ver un arrastre que empieza en otro programa**: la rueda se llama (doble clic, menú de Dolphin y
  Krusader, el atajo a mitad del arrastre, la franja del borde).
- **El atajo** que pone `--instalar` lo toma KDE al volver a entrar en la sesión.
- **MEGA** no está, a pedido del autor. Dropbox, solo si existe su carpeta Dropbox en el inicio.

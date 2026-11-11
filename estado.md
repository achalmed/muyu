---
tipo: estado
estado: activo
actualizado: 2026-11-11
---
# estado.md — muyu (privado y sin remoto)

Lo primero que se lee y lo último que se escribe en cada sesión (regla 10 de la guía raíz). Lo pendiente, aquí, en
§Por hacer, con fecha y dueño.

## Hecho

| fecha | qué | dónde se ve |
|---|---|---|
| 2026-11-11 | **Varias pantallas** (lo vio el autor: la rueda salía siempre en una): la rueda deja que KWin elija la pantalla cada vez que aparece (`wantsToBeOnActiveScreen`: la activa, la del puntero) y la residente pone una franja en cada pantalla, en el borde que no toca a otro monitor (`pantallas.js`), con el QScreen de verdad que layer-shell necesita (`pantallasQt`; desde QML, `screen` no le llegaba y la capa nacía en la principal). Comprobado en el protocolo Wayland con un KWin anidado de dos salidas: cada franja en la suya y la rueda sin fijar ninguna | `escritorio/qml/SuperposicionCapa.qml`, `escritorio/qml/pantallas.js` |
| 2026-11-11 | **Lo que el autor vio en la sesión**: una imagen abierta con Gwenview desde la rueda salía sin marco ni botones y encima de todo (no se podía cerrar): heredaba `QT_WAYLAND_SHELL_INTEGRATION=layer-shell` de Muyu y nacía como capa de superposición. Muyu quita de su entorno lo que solo le sirve a él (la capa, su carpeta en PYTHONPATH, GUI_COMUN_DIR) en cuanto crea su ventana, y `lanzar` arma el entorno de cada aplicación sin eso y en la carpeta del archivo; comprobado en un KWin anidado (Gwenview sin la variable); prueba que lo vigila | `escritorio/aplicacion.py` (`entorno_limpio`), `tests/test_escritorio.py` |
| 2026-11-11 | **La macro de LibreOffice, probada de verdad** (con `libreoffice-script-provider-python`, que el autor instaló): un LibreOffice con perfil aparte carga un documento por UNO, la macro lanza Muyu y la rueda se abre con él. Corregido: con el documento oculto o desde el editor de macros `XSCRIPTCONTEXT.getDocument()` viene vacío; la macro toma el componente actual o el primero abierto con archivo | `muyu/instalar.py` (`contenido_macro`) |
| 2026-11-11 | **Probado con uso real**: enlace de YouTube → «MP3» (avance real de yt-dlp) → «SRT» (Whisper, 26 s) por el controlador; mat2 sobre una foto con GPS, autor y número de serie (quedan 5 de 23 campos, los del formato; el original intacto); ISO real (crear, insertar y comprobar el MD5, información, montar y desmontar con udisksctl); la rueda con layer-shell en un KWin anidado, Intro lanza KOReader y «Abrir con Okular» abre el PDF (y Okular dice por D-Bus qué muestra); la residente responde en 7 ms. Corregido: «Montar ISO» solo conectaba la imagen (ahora la monta y dice dónde); la consulta a Okular, sin la introspección que podía bloquear 25 s; las aplicaciones se lanzan sin heredar la salida de Muyu | `muyu/proveedores/sistema.py`, `escritorio/controlador.py` |
| 2026-11-11 | **Nace Muyu** (M1): la rueda de Raphi mudada aquí con proveedores (Raphi, «Abrir con…», studios, sistema), tres anillos con páginas, rueda vacía con las generales, predeterminada con respaldo y vuelta, Dolphin y Krusader, atajo, franja, macro de LibreOffice; 30 pruebas | `docs/decisiones.md` M1; `tests/` |

## En curso

nada en curso

## Por hacer

- 2026-11-11 · dueño: **el autor** · lo que solo se ve en la sesión real: el doble clic en Dolphin (la rueda bajo el puntero, Intro), Meta+Ctrl+R a mitad de un arrastre tras volver a entrar, la franja del borde, arrastrar el resultado a Dolphin, y lo que necesita el teléfono (Android) o un servidor (SSH, Samba).
- 2026-11-11 · dueño: director · el anillo interior de una carpeta tiene un solo sector (ZIP): pensar si llevar ahí
  las herramientas más usadas de la carpeta.
- 2026-11-11 · dueño: director · remoto privado en GitHub (`gh repo create achalmed/muyu --private`), si el autor lo quiere.

## Futuro

- Un remoto privado y, si sirve, otros proveedores (los demás proyectos del espacio de trabajo con CLI).

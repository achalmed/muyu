---
tipo: decision
estado: activo
genero: explicacion
---
# Decisiones — muyu

### 2026-11-11 · M1: nace Muyu, la rueda universal; la rueda de Raphi se muda aquí

Encargo del autor: que la rueda de soltar (R13 de Raphi) sea la aplicación predeterminada de casi todos los archivos,
con «Abrir con» para las aplicaciones del sistema, que reúna las capacidades de Filesystem, Git, Huella, LaTeX y Quarto
Studio y las de KDE-Services (todas menos MEGA), y que cambie de nombre. Decidido con el autor (2026-11-11):

1. **Proyecto propio y privado**, no dentro de Raphi: Raphi es público (AGPL) y no puede integrar Huella (sensible), y
   la regla de la plataforma impide importar otros proyectos. Muyu llama a cada uno por su CLI (`suite.yml`); Raphi
   sigue siendo el motor de documentos y medios y conserva el corredor como su API de proceso.
2. **Nombre: Muyu** («círculo, giro»), en la línea quechua del ecosistema.
3. **Predeterminada con «Abrir con»**: el doble clic abre la rueda con la aplicación de siempre primero (Intro la
   abre); se respalda `mimeapps.list` y `quitar` lo devuelve todo. Fuera: carpetas, enlaces web, ejecutables, `.desktop`.
4. **KDE-Services, todo menos MEGA**: lo de documentos y medios ya estaba en el motor de Raphi; lo demás (red, ISO,
   seguridad, Android, copias, búsquedas, sistema) es el proveedor `sistema` de Muyu. Diferencias a propósito: carpetas
   cifradas con gocryptfs (EncFS está abandonado), grabar con xorriso (wodim es de 2010), el reemplazo de texto en una
   copia, y lo destructivo con confirmación.

Arquitectura: proveedores (`muyu/proveedores/`) que dicen qué ofrecen y cómo se corre; anillos por páginas; la ventana
(QML + Kirigami sobre gui-comun, layer-shell en Wayland) no nombra operaciones.

### 2026-11-11 · M2: Muyu se publica; varias pantallas

Encargo del autor: publicarlo en GitHub «para que sea mundial», con capturas y etiquetas. Revisa el punto 1 de M1
(privado): Muyu es público como Raphi (AGPL-3.0), con su guarda (`scripts/escanear.py`, el escáner de Tiqsi en cada
envío) y toda su historia, escaneada antes de salir. Nada del repo depende del espacio de trabajo: los proyectos se
encuentran por el manifiesto o al lado, y los studios del autor (privados) son proveedores opcionales. El README va en
español con una sección en inglés para quien llegue de fuera. En el mismo encargo: varias pantallas (la rueda en la del
puntero, que elige KWin; una franja por pantalla en su borde libre), visto por el autor con dos monitores.


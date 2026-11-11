"""Muyu: la rueda universal del escritorio. Suelta un archivo, una carpeta o un enlace (o haz doble clic en un
archivo: Muyu es la aplicación predeterminada) y aparece un círculo bajo el puntero con todo lo que se puede hacer con
eso en esta máquina: abrirlo con cada aplicación que lo conoce, convertirlo, transformarlo, y usar sobre él las
herramientas de tus programas (Raphi, Filesystem Studio, Git Studio, LaTeX Studio, Quarto Studio, Huella Studio) y las
de sistema que traía KDE-Services (red, ISO, seguridad, Android, copias, búsquedas).

Muyu no hace nada por sí mismo que otro proyecto ya haga: cada proveedor (`muyu/proveedores/`) dice qué ofrece para
unas rutas y cómo se corre, y lo corre el programa que lo sabe hacer, por su CLI (el contrato de su `suite.yml`), nunca
importando su código. Este paquete es Python puro (sin Qt); la ventana está en `escritorio/`.
"""
VERSION = "0.1.0"

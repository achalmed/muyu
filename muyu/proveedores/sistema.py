"""El proveedor del sistema: lo de KDE-Services (geobarrod) que no es del dominio de Raphi, menos MEGA, para cualquier
archivo o carpeta y desde la rueda vacía. Grupos (como los submenús de KDE-Services):

- Archivo: estado, permisos, hacer ejecutable, prefijo de fecha, fecha, espacios del nombre, reemplazar texto;
- Seguridad: cifrar y descifrar con GPG (con contraseña o para alguien), firmar y verificar, carpetas cifradas
  (gocryptfs: crear, montar, desmontar), borrado seguro (shred, con confirmación);
- Red: servidor HTTP de una carpeta, SSH (clave, instalarla, conectar, enviar, montar con sshfs y desmontar), Samba
  y FTP/SFTP en Dolphin, conexiones y puertos que escuchan;
- ISO: montar, desmontar, información, MD5 incrustado (comprobar e insertar), grabar, crear de una carpeta, probar el
  arranque en QEMU (BIOS y UEFI);
- Android (adb): dispositivos, enviar, traer, instalar y desinstalar apps, reiniciar (bootloader, recovery);
- Copias: respaldo de configuraciones (KDE, Firefox, Thunderbird, SSH, GnuPG, Zen, Chrome…) a un .tar.gz con fecha;
  Dropbox (copiar y mover a la carpeta de Dropbox);
- Búsqueda: por nombre, por texto, lo modificado hace poco, en todo el disco (plocate), espacio usado;
- Sistema: información, procesos, errores en vivo, actualizaciones; Konsole y Midnight Commander aquí (también root);
  paquetes .deb y .rpm (información, contenido, instalar); scripts (ejecutar, como root).

Lo que necesita root o es interactivo se abre en Konsole (la contraseña la escribe la persona allí). Lo que destruye o
renombra pide confirmarlo. Cada acción dice qué programas necesita: si falta uno, la rueda lo muestra.
"""
from __future__ import annotations

import datetime as dt
import shlex
import shutil
from pathlib import Path

NOMBRE = "sistema"
ISO = (".iso", ".img")
APK = (".apk",)
DEB = (".deb",)
RPM = (".rpm",)
SCRIPTS = (".sh", ".bash", ".py", ".pl", ".run", ".AppImage", ".appimage")
GPG = (".gpg", ".asc", ".pgp")
FIRMAS = (".sig",)
TEXTO = (".txt", ".md", ".csv", ".tsv", ".json", ".yml", ".yaml", ".xml", ".html", ".htm", ".tex", ".qmd", ".py", ".sh",
         ".ini", ".conf", ".cfg", ".log", ".srt", ".vtt", ".css", ".js", ".ts")
CONFIRMAR = {"clave": "confirmo", "etiqueta": "Entiendo lo que hace y quiero hacerlo", "tipo": "casilla", "defecto": False,
             "obligatorio": True}
CONFIGURACIONES = {"KDE y Plasma": [".config/kdeglobals", ".config/plasma*", ".config/kwin*", ".config/k*rc", ".local/share/plasma",
                                    ".local/share/kxmlgui5"],
                   "Firefox": [".mozilla"], "Zen": [".zen", ".var/app/app.zen_browser.zen"], "Thunderbird": [".thunderbird"],
                   "Chrome": [".config/google-chrome"], "SSH": [".ssh"], "GnuPG": [".gnupg"], "Git": [".gitconfig"],
                   "Konsole": [".local/share/konsole", ".config/konsolerc"], "Obsidian": [".config/obsidian"],
                   "VS Code": [".config/Code/User"], "Shell": [".bashrc", ".zshrc", ".profile"]}


def _p(clave, etiqueta, tipo="texto", defecto=None, **kw) -> dict:
    return {"clave": clave, "etiqueta": etiqueta, "tipo": tipo, "defecto": defecto, "opciones": kw.pop("opciones", []),
            "ayuda": kw.pop("ayuda", ""), "obligatorio": kw.pop("obligatorio", False), **kw}


# (id, grupo, etiqueta, título, descripción, icono, cuándo, requiere, parámetros)
# cuándo: "archivo" (uno o más archivos), "uno" (un archivo), "carpeta" (una carpeta), "vacia" (la rueda vacía),
#         o una tupla de extensiones (todos los archivos con una de ellas)
ACCIONES: tuple = (
    # --- Archivo
    ("estado", "Archivo", "Estado", "Estado del archivo", "Tamaño, permisos, dueño, fechas, inodo (stat)", "documentinfo", "archivo", ("stat",), []),
    ("permisos", "Archivo", "Permisos…", "Cambiar los permisos", "Con chmod (p. ej. 644, 755, u+x)", "document-edit", "archivo", ("chmod",),
     [_p("modo", "Permisos", "texto", "644", obligatorio=True), CONFIRMAR]),
    ("ejecutable", "Archivo", "Hacer ejecutable", "Hacer ejecutable (chmod u+x)", "Para un script o un AppImage", "system-run", "archivo", ("chmod",), []),
    ("prefijo_fecha", "Archivo", "Prefijo de fecha", "Poner la fecha al principio del nombre", "2026-11-11_nombre.ext (con la fecha de modificación)",
     "view-calendar-day", "archivo", (), [CONFIRMAR]),
    ("espacios", "Archivo", "Sin espacios", "Cambiar los espacios del nombre por _", "Nombre con guiones bajos (también en carpetas)", "edit-rename",
     "archivo_o_carpeta", (), [CONFIRMAR]),
    ("fecha", "Archivo", "Cambiar fecha…", "Cambiar la fecha de modificación", "touch -d (vacío: ahora)", "view-calendar", "archivo", ("touch",),
     [_p("fecha", "Fecha (AAAA-MM-DD HH:MM)", "texto", "")]),
    ("reemplazar", "Archivo", "Reemplazar texto…", "Reemplazar un texto (en una copia)", "Deja <nombre>_reemplazado al lado; el original no se toca",
     "edit-find-replace", TEXTO, (), [_p("buscar", "Buscar", obligatorio=True), _p("cambiar", "Cambiar por", "texto", "")]),
    # --- Seguridad
    ("cifrar", "Seguridad", "Cifrar (GPG)", "Cifrar con contraseña (GPG, AES-256)", "Deja <nombre>.gpg; la contraseña la pide GnuPG",
     "document-encrypt", "archivo", ("gpg",), []),
    ("cifrar_para", "Seguridad", "Cifrar para…", "Cifrar para alguien (su clave pública)", "Solo esa persona podrá abrirlo", "document-encrypt",
     "archivo", ("gpg",), [_p("destinatario", "Correo o ID de la clave", obligatorio=True)]),
    ("descifrar", "Seguridad", "Descifrar", "Descifrar (GPG)", "Deja el archivo original al lado", "document-decrypt", GPG, ("gpg",), []),
    ("firmar", "Seguridad", "Firmar (GPG)", "Firmar con tu clave GPG", "Deja <nombre>.sig al lado", "document-sign", "archivo", ("gpg",), []),
    ("verificar_firma", "Seguridad", "Verificar firma", "Verificar la firma GPG", "Contra el archivo de al lado (sin .sig)", "security-high",
     FIRMAS, ("gpg",), []),
    ("triturar", "Seguridad", "Borrado seguro…", "Borrado seguro (shred)", "Sobrescribe 3 veces y borra. NO SE PUEDE DESHACER", "edit-delete-shred",
     "archivo", ("shred",), [CONFIRMAR]),
    ("cifrada_crear", "Seguridad", "Carpeta cifrada…", "Crear una carpeta cifrada aquí (gocryptfs)", "En Konsole: la contraseña y su clave maestra",
     "folder-locked", "carpeta", ("gocryptfs", "konsole"), [_p("nombre", "Nombre de la carpeta", "texto", "Cifrada", obligatorio=True)]),
    ("cifrada_montar", "Seguridad", "Abrir cifrada", "Abrir esta carpeta cifrada (gocryptfs)", "La monta en <carpeta>_abierta", "folder-unlocked",
     "gocryptfs", ("gocryptfs", "konsole"), []),
    ("cifrada_cerrar", "Seguridad", "Cerrar cifrada", "Cerrar esta carpeta cifrada abierta", "fusermount -u", "folder-locked", "montada", ("fusermount3",), []),
    # --- Red
    ("http", "Red", "Servidor HTTP", "Servir esta carpeta por HTTP (en Konsole)", "http://<tu IP>:8000 en la red local; Ctrl+C la cierra",
     "network-server", "carpeta", ("python3", "konsole"), [_p("puerto", "Puerto", "entero", 8000)]),
    ("ssh_clave", "Red", "Clave SSH", "Generar tu clave SSH (ed25519)", "Paso 1 antes de conectar sin contraseña (en Konsole)", "dialog-password",
     "vacia", ("ssh-keygen", "konsole"), []),
    ("ssh_instalar", "Red", "Instalar clave…", "Instalar tu clave en un servidor", "Paso 2: ssh-copy-id (en Konsole)", "network-connect", "vacia",
     ("ssh-copy-id", "konsole"), [_p("servidor", "usuario@servidor", obligatorio=True)]),
    ("ssh_conectar", "Red", "SSH…", "Conectar por SSH (en Konsole)", "usuario@servidor", "utilities-terminal", "vacia", ("ssh", "konsole"),
     [_p("servidor", "usuario@servidor", obligatorio=True)]),
    ("ssh_enviar", "Red", "Enviar por SSH…", "Enviar por SSH (scp)", "A una carpeta del servidor (en Konsole)", "document-send", "archivo",
     ("scp", "konsole"), [_p("destino", "usuario@servidor:carpeta", obligatorio=True)]),
    ("sshfs", "Red", "Montar remota…", "Montar una carpeta remota aquí (sshfs)", "La carpeta del servidor aparece dentro de esta", "folder-remote",
     "carpeta", ("sshfs",), [_p("remota", "usuario@servidor:carpeta", obligatorio=True), _p("nombre", "Nombre del punto de montaje", "texto", "remota")]),
    ("desmontar", "Red", "Desmontar", "Desmontar esta carpeta (sshfs, gocryptfs)", "fusermount -u", "media-eject", "montada", ("fusermount3",), []),
    ("samba", "Red", "Samba…", "Abrir un recurso compartido (Samba) en Dolphin", "smb://servidor/recurso", "folder-remote", "vacia", ("dolphin",),
     [_p("recurso", "servidor/recurso", obligatorio=True)]),
    ("sftp", "Red", "FTP o SFTP…", "Conectar por FTP o SFTP en Dolphin", "sftp://usuario@servidor o ftp://servidor", "folder-remote", "vacia",
     ("dolphin",), [_p("direccion", "Dirección", "texto", "sftp://", obligatorio=True)]),
    ("conexiones", "Red", "Conexiones", "Conexiones establecidas", "ss -tunp", "network-connect", "vacia", ("ss",), []),
    ("puertos", "Red", "Puertos abiertos", "Puertos que escuchan", "ss -tulnp", "network-server", "vacia", ("ss",), []),
    # --- ISO
    ("iso_montar", "ISO", "Montar ISO", "Montar la imagen (solo lectura)", "udisksctl: aparece en Dolphin", "media-mount", ISO, ("udisksctl",), []),
    ("iso_desmontar", "ISO", "Desmontar ISO", "Desmontar la imagen", "La suelta del dispositivo de bucle", "media-eject", ISO, ("udisksctl", "losetup"), []),
    ("iso_info", "ISO", "Información ISO", "Información de la imagen ISO-9660", "isoinfo -d", "documentinfo", ISO, ("isoinfo",), []),
    ("iso_md5", "ISO", "Comprobar MD5", "Comprobar el MD5 incrustado", "checkisomd5 (paquete isomd5sum)", "security-high", ISO, ("checkisomd5",), []),
    ("iso_md5_poner", "ISO", "Insertar MD5", "Insertar el MD5 en la ISO", "implantisomd5: la ISO cambia", "document-edit", ISO, ("implantisomd5",), [CONFIRMAR]),
    ("iso_grabar", "ISO", "Grabar…", "Grabar en un disco óptico (en Konsole)", "xorriso como cdrecord", "media-optical-burn", ISO, ("xorriso", "konsole"),
     [_p("unidad", "Unidad", "texto", "/dev/sr0", obligatorio=True), CONFIRMAR]),
    ("iso_qemu", "ISO", "Probar (BIOS)", "Probar el arranque en QEMU (BIOS)", "Una máquina de 2 GB; nada se instala", "computer", ISO,
     ("qemu-system-x86_64",), []),
    ("iso_qemu_uefi", "ISO", "Probar (UEFI)", "Probar el arranque en QEMU (UEFI)", "Con OVMF", "computer", ISO, ("qemu-system-x86_64",), []),
    ("iso_crear", "ISO", "Crear ISO", "Crear una ISO de esta carpeta", "xorriso (Joliet y Rock Ridge)", "media-optical", "carpeta", ("xorriso",), []),
    # --- Android
    ("adb_dispositivos", "Android", "Android", "Android: los dispositivos conectados", "adb devices -l", "smartphone", "vacia", ("adb",), []),
    ("adb_enviar", "Android", "Al teléfono", "Enviar al teléfono (Download)", "adb push a /sdcard/Download", "smartphone", "archivo", ("adb",),
     [_p("carpeta", "Carpeta del teléfono", "texto", "/sdcard/Download")]),
    ("adb_traer", "Android", "Del teléfono…", "Traer del teléfono a esta carpeta", "adb pull", "smartphone", "carpeta", ("adb",),
     [_p("origen", "Ruta en el teléfono", "texto", "/sdcard/DCIM/Camera", obligatorio=True)]),
    ("adb_instalar", "Android", "Instalar APK", "Instalar en el teléfono", "adb install -r", "package-install", APK, ("adb",), []),
    ("adb_desinstalar", "Android", "Desinstalar app…", "Desinstalar una app del teléfono", "adb uninstall <paquete>", "package-remove", "vacia", ("adb",),
     [_p("paquete", "Paquete (com.ejemplo.app)", obligatorio=True), CONFIRMAR]),
    ("adb_reiniciar", "Android", "Reiniciar…", "Reiniciar el teléfono", "Normal, al bootloader o a recovery", "system-reboot", "vacia", ("adb",),
     [_p("modo", "A", "opcion", "", opciones=[["", "Normal"], ["bootloader", "Bootloader"], ["recovery", "Recovery"]])]),
    ("adb_respaldo", "Android", "Respaldo Android", "Respaldo de fotos y descargas del teléfono", "adb pull de DCIM, Pictures y Download a esta carpeta",
     "folder-download", "carpeta", ("adb",), []),
    # --- Copias y Dropbox
    ("respaldo_config", "Copias", "Respaldar config…", "Respaldar configuraciones a esta carpeta", "Un .tar.gz con fecha: KDE, navegadores, correo, SSH, GnuPG…",
     "document-save-all", "carpeta", ("tar",), [_p("que", "Qué", "opcion", "todo", opciones=[["todo", "Todo lo de la lista"]] + [[k, k] for k in CONFIGURACIONES])]),
    ("dropbox_copiar", "Copias", "A Dropbox", "Copiar a la carpeta de Dropbox", "~/Dropbox (el cliente de Dropbox lo sube)", "folder-cloud", "archivo",
     ("dropbox",), []),
    # --- Búsqueda
    ("buscar_nombre", "Búsqueda", "Buscar nombre…", "Buscar por nombre aquí", "find, sin distinguir mayúsculas", "edit-find", "carpeta", ("find",),
     [_p("texto", "Parte del nombre", obligatorio=True)]),
    ("buscar_texto", "Búsqueda", "Buscar texto…", "Buscar un texto dentro de los archivos", "grep -rIl", "edit-find", "carpeta", ("grep",),
     [_p("texto", "Texto", obligatorio=True)]),
    ("recientes", "Búsqueda", "Modificados", "Lo modificado hace poco aquí", "find -mtime", "document-open-recent", "carpeta", ("find",),
     [_p("dias", "Días", "entero", 7)]),
    ("locate", "Búsqueda", "Buscar en el disco…", "Buscar en todo el disco (plocate)", "Rápido: usa la base de updatedb", "edit-find", "vacia",
     ("plocate",), [_p("texto", "Nombre", obligatorio=True)]),
    ("espacio", "Búsqueda", "Espacio usado", "Espacio que ocupa cada cosa aquí", "du, de mayor a menor", "view-statistics", "carpeta", ("du",), []),
    # --- Sistema y terminal
    ("info_sistema", "Sistema", "Info del sistema", "Información del sistema", "fastfetch (o inxi)", "computer", "vacia", (), []),
    ("procesos", "Sistema", "Procesos", "Monitor de procesos (htop, en Konsole)", "q para salir", "utilities-system-monitor", "vacia", ("htop", "konsole"), []),
    ("errores", "Sistema", "Errores en vivo", "Errores del sistema en vivo (en Konsole)", "journalctl -f -p err", "dialog-warning", "vacia",
     ("journalctl", "konsole"), []),
    ("actualizaciones", "Sistema", "Actualizaciones", "Paquetes con actualización", "apt list --upgradable", "system-software-update", "vacia", ("apt",), []),
    ("konsole", "Sistema", "Konsole aquí", "Abrir Konsole en esta carpeta", "", "utilities-terminal", "carpeta", ("konsole",), []),
    ("mc", "Sistema", "Midnight Commander", "Midnight Commander aquí (en Konsole)", "mc", "system-file-manager", "carpeta", ("mc", "konsole"), []),
    ("mc_root", "Sistema", "MC como root", "Midnight Commander como root (en Konsole)", "sudo mc: la contraseña en Konsole", "system-file-manager",
     "carpeta", ("mc", "konsole"), []),
    ("deb_info", "Sistema", "Info del paquete", "Información del paquete .deb", "dpkg-deb -I", "documentinfo", DEB, ("dpkg-deb",), []),
    ("deb_contenido", "Sistema", "Contenido", "Contenido del paquete .deb", "dpkg-deb -c", "view-list-text", DEB, ("dpkg-deb",), []),
    ("deb_instalar", "Sistema", "Instalar paquete", "Instalar el paquete (en Konsole)", "sudo apt install ./paquete.deb", "package-install", DEB,
     ("apt", "konsole"), []),
    ("rpm_info", "Sistema", "Info del RPM", "Información, cambios y dependencias del .rpm", "rpm -qip", "documentinfo", RPM, ("rpm",), []),
    ("ejecutar", "Sistema", "Ejecutar", "Ejecutar (en Konsole)", "", "system-run", SCRIPTS, ("konsole",), []),
    ("ejecutar_root", "Sistema", "Ejecutar como root", "Ejecutar como root (en Konsole)", "sudo: la contraseña en Konsole", "system-run", SCRIPTS,
     ("konsole",), [CONFIRMAR]),
)
ICONO_GRUPO = {"Archivo": "document-properties", "Seguridad": "security-high", "Red": "network-workgroup", "ISO": "media-optical",
               "Android": "smartphone", "Copias": "document-save-all", "Búsqueda": "edit-find", "Sistema": "computer"}


def _montada(p: Path) -> bool:
    try:
        return p.is_dir() and p.is_mount()
    except OSError:
        return False


def _cuadra(cuando, rutas_: list[Path]) -> bool:
    if not rutas_:
        return cuando == "vacia"
    if cuando == "vacia":
        return False
    uno = len(rutas_) == 1
    if isinstance(cuando, tuple):
        return all(r.is_file() and r.suffix.lower() in cuando for r in rutas_)
    if cuando == "archivo":
        return all(r.is_file() for r in rutas_)
    if cuando == "archivo_o_carpeta":
        return True
    if cuando == "carpeta":
        return uno and rutas_[0].is_dir() and not _montada(rutas_[0])
    if cuando == "montada":
        return uno and _montada(rutas_[0])
    if cuando == "gocryptfs":
        return uno and rutas_[0].is_dir() and (rutas_[0] / "gocryptfs.conf").is_file()
    return False


def opciones(rutas_: list[str]) -> list[dict]:
    if any(r.startswith(("http://", "https://")) for r in rutas_):
        return []
    ps = [Path(r) for r in rutas_]
    salida = []
    for ident, grupo, etiqueta, titulo, desc, icono, cuando, requiere, parametros in ACCIONES:
        if not _cuadra(cuando, ps):
            continue
        faltan = [r for r in requiere if not shutil.which(r)]
        if ident == "info_sistema" and not (shutil.which("fastfetch") or shutil.which("inxi")):
            faltan = ["fastfetch"]
        if ident == "dropbox_copiar" and (Path.home() / "Dropbox").is_dir():
            faltan = []
        salida.append({"proveedor": NOMBRE, "operacion": f"sistema:{ident}", "clave": f"sistema|{ident}", "a": None,
                       "etiqueta": etiqueta, "titulo": f"{grupo} · {titulo}", "descripcion": desc, "icono": icono,
                       "params": {}, "parametros": list(parametros), "pide": bool(parametros), "faltan": faltan,
                       "sin_archivos": cuando == "vacia", "grupo": grupo, "categoria": grupo})
    return salida


def _konsole(orden: str, cwd: str = "") -> dict:
    return {"argv": ["bash", "-lc", orden], "terminal": True, "mantener": True, "cwd": cwd}


def _q(x) -> str:
    return shlex.quote(str(x))


def _libre(p: Path) -> Path:
    """Un nombre que no pisa nada: «x», «x-2», «x-3»…"""
    n, destino = 2, p
    while destino.exists():
        destino = p.with_name(f"{p.stem}-{n}{p.suffix}")
        n += 1
    return destino


def preparar(s: dict, params: dict, archivos: list[str]) -> dict:
    """{argv, cwd, resultado, carpeta, terminal, mantener} para la ventana."""
    op = s["operacion"].split(":", 1)[1]
    ps = [Path(a) for a in archivos]
    p = ps[0] if ps else None
    carpeta = str(p if p and p.is_dir() else p.parent) if p else str(Path.home())
    if any(c["clave"] == "confirmo" for c in s.get("campos", [])) and not params.get("confirmo"):
        raise PermissionError("Falta confirmarlo: marca «Entiendo lo que hace y quiero hacerlo».")
    todos = " ".join(_q(x) for x in ps)
    sh = lambda orden, **kw: {"argv": ["bash", "-c", orden], **kw}  # noqa: E731
    # --- Archivo
    if op == "estado":
        return sh(f"stat {todos}", resultado="informe")
    if op == "permisos":
        return sh(f"chmod {_q(params['modo'])} {todos} && stat -c '%A %n' {todos}", resultado="informe")
    if op == "ejecutable":
        return sh(f"chmod u+x {todos} && stat -c '%A %n' {todos}", resultado="informe")
    if op == "prefijo_fecha":
        nuevos = [_libre(x.with_name(dt.date.fromtimestamp(x.stat().st_mtime).isoformat() + "_" + x.name)) for x in ps]
        return sh(" && ".join(f"mv -n {_q(a)} {_q(b)}" for a, b in zip(ps, nuevos)), resultado="archivos", carpeta=carpeta)
    if op == "espacios":
        nuevos = [_libre(x.with_name(x.name.replace(" ", "_"))) if " " in x.name else x for x in ps]
        return sh(" && ".join(f"mv -n {_q(a)} {_q(b)}" for a, b in zip(ps, nuevos) if a != b) or "true",
                  resultado="archivos", carpeta=carpeta)
    if op == "fecha":
        return sh(f"touch {('-d ' + _q(params['fecha'])) if params.get('fecha') else ''} {todos} && stat -c '%y %n' {todos}", resultado="informe")
    if op == "reemplazar":
        destino = _libre(p.with_name(f"{p.stem}_reemplazado{p.suffix}"))
        codigo = ("import sys; t=open(sys.argv[1],encoding='utf-8',errors='surrogateescape').read(); "
                  "open(sys.argv[2],'w',encoding='utf-8',errors='surrogateescape').write(t.replace(sys.argv[3],sys.argv[4])); "
                  "print('reemplazos:', t.count(sys.argv[3]))")
        return {"argv": ["python3", "-c", codigo, str(p), str(destino), params["buscar"], params.get("cambiar", "")],
                "resultado": "archivos", "carpeta": carpeta}
    # --- Seguridad
    if op == "cifrar":
        return sh(" && ".join(f"gpg --batch --yes --symmetric --cipher-algo AES256 -o {_q(_libre(Path(str(x) + '.gpg')))} {_q(x)}"
                              .replace("--batch --yes ", "") for x in ps), resultado="archivos", carpeta=carpeta)
    if op == "cifrar_para":
        return sh(" && ".join(f"gpg --encrypt --recipient {_q(params['destinatario'])} -o {_q(_libre(Path(str(x) + '.gpg')))} {_q(x)}"
                              for x in ps), resultado="archivos", carpeta=carpeta)
    if op == "descifrar":
        return sh(" && ".join(f"gpg --decrypt -o {_q(_libre(x.with_suffix('')))} {_q(x)}" for x in ps), resultado="archivos", carpeta=carpeta)
    if op == "firmar":
        return sh(" && ".join(f"gpg --detach-sign -o {_q(_libre(Path(str(x) + '.sig')))} {_q(x)}" for x in ps), resultado="archivos", carpeta=carpeta)
    if op == "verificar_firma":
        return sh(f"gpg --verify {_q(p)} {_q(p.with_suffix(''))} 2>&1", resultado="informe")
    if op == "triturar":
        return sh(f"shred -u -n 3 -z -v {todos} 2>&1", resultado="informe")
    if op == "cifrada_crear":
        base = Path(carpeta) / params["nombre"]
        return _konsole(f"mkdir -p {_q(base)} && gocryptfs -init {_q(base)} && echo 'Lista: ábrela desde Muyu con «Abrir cifrada».'", carpeta)
    if op == "cifrada_montar":
        punto = _libre(p.with_name(p.name + "_abierta"))
        return _konsole(f"mkdir -p {_q(punto)} && gocryptfs {_q(p)} {_q(punto)} && dolphin {_q(punto)} &", carpeta)
    if op in ("cifrada_cerrar", "desmontar"):
        return sh(f"fusermount3 -u {_q(p)} && echo 'Desmontada: {p.name}'", resultado="informe")
    # --- Red
    if op == "http":
        return _konsole(f"echo 'Sirviendo {p} en el puerto {int(params.get('puerto') or 8000)} (Ctrl+C para parar)'; "
                        f"hostname -I; python3 -m http.server {int(params.get('puerto') or 8000)}", str(p))
    if op == "ssh_clave":
        return _konsole("ssh-keygen -t ed25519")
    if op == "ssh_instalar":
        return _konsole(f"ssh-copy-id {_q(params['servidor'])}")
    if op == "ssh_conectar":
        return _konsole(f"ssh {_q(params['servidor'])}")
    if op == "ssh_enviar":
        return _konsole(f"scp -r {todos} {_q(params['destino'])}")
    if op == "sshfs":
        punto = _libre(p / (params.get("nombre") or "remota"))
        return sh(f"mkdir -p {_q(punto)} && sshfs {_q(params['remota'])} {_q(punto)} -o reconnect && echo 'Montada en {punto}'", resultado="informe")
    if op == "samba":
        return {"argv": ["dolphin", "--new-window", "smb://" + params["recurso"].removeprefix("smb://").lstrip("/")], "terminal": False,
                "resultado": "nada", "suelto": True}
    if op == "sftp":
        return {"argv": ["dolphin", "--new-window", params["direccion"]], "resultado": "nada", "suelto": True}
    if op == "conexiones":
        return sh("ss -tunp state established 2>/dev/null", resultado="informe")
    if op == "puertos":
        return sh("ss -tulnp 2>/dev/null", resultado="informe")
    # --- ISO
    if op == "iso_montar":
        # udisksctl conecta la imagen a un dispositivo de bucle; no siempre la monta sola: se monta y se dice dónde
        return sh(f"d=$(udisksctl loop-setup -r -f {_q(p)} 2>&1 | sed -n 's|.* as \\(/dev/loop[0-9]*\\)\\.$|\\1|p'); "
                  "[ -n \"$d\" ] || { echo 'No se pudo conectar la imagen.'; exit 1; }; sleep 1; "
                  "udisksctl mount -b \"$d\" >/dev/null 2>&1; m=$(lsblk -no MOUNTPOINT \"$d\" | head -1); "
                  "[ -n \"$m\" ] || { echo \"Conectada en $d, pero no se pudo montar.\"; exit 1; }; "
                  "echo \"Dispositivo: $d\"; echo \"Montada en: $m\"", resultado="informe")
    if op == "iso_desmontar":
        return sh(f"for d in $(losetup -j {_q(p)} | cut -d: -f1); do udisksctl unmount -b $d 2>/dev/null; udisksctl loop-delete -b $d && echo \"Suelta: $d\"; done",
                  resultado="informe")
    if op == "iso_info":
        return sh(f"isoinfo -d -i {_q(p)}", resultado="informe")
    if op == "iso_md5":
        return sh(f"checkisomd5 --verbose {_q(p)} 2>&1", resultado="informe")
    if op == "iso_md5_poner":
        return sh(f"implantisomd5 {_q(p)} 2>&1", resultado="informe")
    if op == "iso_grabar":
        return _konsole(f"xorriso -as cdrecord -v dev={_q(params['unidad'])} -eject {_q(p)}")
    if op in ("iso_qemu", "iso_qemu_uefi"):
        uefi = ""
        if op == "iso_qemu_uefi":
            ovmf = next((f for f in ("/usr/share/OVMF/OVMF_CODE_4M.fd", "/usr/share/ovmf/OVMF.fd", "/usr/share/OVMF/OVMF_CODE.fd") if Path(f).is_file()), "")
            uefi = f"-drive if=pflash,format=raw,readonly=on,file={ovmf}" if ovmf else ""
        return {"argv": ["bash", "-c", f"qemu-system-x86_64 -enable-kvm -m 2048 -smp 2 {uefi} -cdrom {_q(p)} -boot d"], "resultado": "nada",
                "suelto": True}
    if op == "iso_crear":
        destino = _libre(p.with_suffix(".iso") if p.suffix else Path(str(p) + ".iso"))
        return sh(f"xorriso -as mkisofs -J -R -V {_q(p.name[:32])} -o {_q(destino)} {_q(p)} 2>&1", resultado="archivos", carpeta=str(p.parent))
    # --- Android
    if op == "adb_dispositivos":
        return sh("adb devices -l", resultado="informe")
    if op == "adb_enviar":
        return sh(f"adb push {todos} {_q(params.get('carpeta') or '/sdcard/Download')}", resultado="informe")
    if op == "adb_traer":
        return sh(f"adb pull {_q(params['origen'])} {_q(p)}", resultado="archivos", carpeta=str(p))
    if op == "adb_instalar":
        return sh(" && ".join(f"adb install -r {_q(x)}" for x in ps), resultado="informe")
    if op == "adb_desinstalar":
        return sh(f"adb uninstall {_q(params['paquete'])}", resultado="informe")
    if op == "adb_reiniciar":
        return sh(f"adb reboot {_q(params['modo'])}" if params.get("modo") else "adb reboot", resultado="nada")
    if op == "adb_respaldo":
        destino = p / f"android-{dt.date.today().isoformat()}"
        return sh(f"mkdir -p {_q(destino)} && for c in DCIM Pictures Download Documents; do adb pull /sdcard/$c {_q(destino)}/ ; done",
                  resultado="archivos", carpeta=str(p))
    # --- Copias y Dropbox
    if op == "respaldo_config":
        que = params.get("que") or "todo"
        patrones = [x for k, v in CONFIGURACIONES.items() if que in ("todo", k) for x in v]
        destino = _libre(p / f"configuraciones-{que.replace(' ', '_').lower()}-{dt.date.today().isoformat()}.tar.gz")
        lista = " ".join(patrones)
        return sh(f"cd ~ && shopt -s nullglob && set -- {lista} && tar -czf {_q(destino)} --ignore-failed-read \"$@\" 2>&1 && "
                  f"echo \"Respaldo: {destino.name} ($# rutas)\"", resultado="archivos", carpeta=str(p))
    if op == "dropbox_copiar":
        return sh(f"cp -n -r {todos} ~/Dropbox/ && echo 'Copiado a ~/Dropbox'", resultado="informe")
    # --- Búsqueda
    if op == "buscar_nombre":
        return sh(f"find {_q(p)} -iname {_q('*' + params['texto'] + '*')} -not -path '*/.git/*' 2>/dev/null | head -500", resultado="informe")
    if op == "buscar_texto":
        return sh(f"grep -rIl --exclude-dir=.git --exclude-dir=node_modules -- {_q(params['texto'])} {_q(p)} 2>/dev/null | head -500", resultado="informe")
    if op == "recientes":
        return sh(f"find {_q(p)} -type f -mtime -{int(params.get('dias') or 7)} -not -path '*/.git/*' -printf '%TY-%Tm-%Td %TH:%TM  %p\\n' 2>/dev/null | sort -r | head -300",
                  resultado="informe")
    if op == "locate":
        return sh(f"plocate -i -l 500 -- {_q(params['texto'])}", resultado="informe")
    if op == "espacio":
        return sh(f"du -h --max-depth=1 {_q(p)} 2>/dev/null | sort -rh | head -60", resultado="informe")
    # --- Sistema y terminal
    if op == "info_sistema":
        return sh("fastfetch --pipe 2>/dev/null || inxi -Fxz -c0", resultado="informe")
    if op == "procesos":
        return _konsole("htop")
    if op == "errores":
        return _konsole("journalctl -f -p err")
    if op == "actualizaciones":
        return sh("apt list --upgradable 2>/dev/null | tail -n +2", resultado="informe")
    if op == "konsole":
        return {"argv": ["konsole", "--workdir", str(p)], "resultado": "nada", "suelto": True}
    if op == "mc":
        return _konsole("mc", str(p))
    if op == "mc_root":
        return _konsole("sudo mc", str(p))
    if op == "deb_info":
        return sh(f"dpkg-deb -I {_q(p)}", resultado="informe")
    if op == "deb_contenido":
        return sh(f"dpkg-deb -c {_q(p)} | head -400", resultado="informe")
    if op == "deb_instalar":
        return _konsole(f"sudo apt install {_q(p)}")
    if op == "rpm_info":
        return sh(f"rpm -qip {_q(p)} && echo && rpm -qp --changelog {_q(p)} | head -40 && echo && rpm -qpR {_q(p)}", resultado="informe")
    if op == "ejecutar":
        return _konsole(_q(p), carpeta)
    if op == "ejecutar_root":
        return _konsole("sudo " + _q(p), carpeta)
    raise LookupError(f"El sistema no sabe «{op}».")

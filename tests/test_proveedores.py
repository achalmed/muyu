"""Los proveedores de los studios y del sistema: qué ofrecen para cada cosa y que sus órdenes hagan lo que dicen. Las
órdenes seguras se corren de verdad sobre carpetas temporales (estado, buscar, espacio, renombrar sin pisar, reemplazar
en una copia, cifrar y descifrar con GPG en un llavero temporal, contar con Filesystem Studio, el estado de un repo);
lo que destruye exige confirmarlo; lo interactivo va a Konsole. Nada toca la red ni la sesión."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from muyu import rutas
from muyu.proveedores import sistema, studios


def _correr(plan: dict, **env) -> subprocess.CompletedProcess:
    return subprocess.run(plan["argv"], cwd=plan.get("cwd") or None, capture_output=True, text=True, timeout=60,
                          env={**os.environ, **env}, errors="replace")


def _sector(proveedor, rutas_, etiqueta):
    o = next(x for x in proveedor.opciones([str(r) for r in rutas_]) if x["etiqueta"] == etiqueta)
    from muyu import anillos
    return anillos.sector(o)


# --- sistema ---------------------------------------------------------------------------------------------------------


def test_sistema_ofrece_segun_lo_que_hay(tmp_path):
    archivo = tmp_path / "a.txt"
    archivo.write_text("hola")
    iso = tmp_path / "x.iso"
    iso.write_bytes(b"\0" * 10)
    general = {o["etiqueta"] for o in sistema.opciones([])}
    assert {"SSH…", "Android", "Info del sistema", "Puertos abiertos"} <= general
    de_archivo = {o["etiqueta"] for o in sistema.opciones([str(archivo)])}
    assert {"Cifrar (GPG)", "Borrado seguro…", "Reemplazar texto…", "Estado"} <= de_archivo and "Montar ISO" not in de_archivo
    assert {"Montar ISO", "Probar (UEFI)", "Información ISO"} <= {o["etiqueta"] for o in sistema.opciones([str(iso)])}
    de_carpeta = {o["etiqueta"] for o in sistema.opciones([str(tmp_path)])}
    assert {"Servidor HTTP", "Crear ISO", "Buscar texto…", "Respaldar config…", "Konsole aquí"} <= de_carpeta
    assert sistema.opciones(["https://a.org"]) == []
    assert all(o["proveedor"] == "sistema" and o["clave"].startswith("sistema|") for o in sistema.opciones([str(archivo)]))


def test_sistema_corre_lo_seguro(tmp_path):
    archivo = tmp_path / "datos uno.txt"
    archivo.write_text("hola mundo, hola")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "buscado.md").write_text("aguja")
    r = _correr(sistema.preparar(_sector(sistema, [archivo], "Estado"), {}, [str(archivo)]))
    assert r.returncode == 0 and "datos uno.txt" in r.stdout
    r = _correr(sistema.preparar(_sector(sistema, [tmp_path], "Buscar texto…"), {"texto": "aguja"}, [str(tmp_path)]))
    assert "buscado.md" in r.stdout
    r = _correr(sistema.preparar(_sector(sistema, [tmp_path], "Buscar nombre…"), {"texto": "BUSCA"}, [str(tmp_path)]))
    assert "buscado.md" in r.stdout
    assert _correr(sistema.preparar(_sector(sistema, [tmp_path], "Espacio usado"), {}, [str(tmp_path)])).returncode == 0
    plan = sistema.preparar(_sector(sistema, [archivo], "Reemplazar texto…"), {"buscar": "hola", "cambiar": "adiós"}, [str(archivo)])
    r = _correr(plan)
    assert r.returncode == 0 and "reemplazos: 2" in r.stdout
    assert (tmp_path / "datos uno_reemplazado.txt").read_text() == "adiós mundo, adiós" and archivo.read_text() == "hola mundo, hola"


def test_lo_que_destruye_o_renombra_pide_confirmarlo(tmp_path):
    archivo = tmp_path / "con espacios.txt"
    archivo.write_text("x")
    for etiqueta in ("Borrado seguro…", "Sin espacios", "Prefijo de fecha", "Permisos…"):
        s = _sector(sistema, [archivo], etiqueta)
        assert s["pide"]
        with pytest.raises(PermissionError):
            sistema.preparar(s, {}, [str(archivo)])
    ocupado = tmp_path / "con_espacios.txt"
    ocupado.write_text("ya estaba")                              # el nombre nuevo no pisa lo que hay
    r = _correr(sistema.preparar(_sector(sistema, [archivo], "Sin espacios"), {"confirmo": True}, [str(archivo)]))
    assert r.returncode == 0 and ocupado.read_text() == "ya estaba" and (tmp_path / "con_espacios-2.txt").is_file()
    nuevo = tmp_path / "con_espacios-2.txt"
    assert sistema.preparar(_sector(sistema, [nuevo], "Borrado seguro…"), {"confirmo": True}, [str(nuevo)])["argv"][-1].startswith("shred")


@pytest.mark.skipif(not shutil.which("gpg"), reason="sin gpg")
def test_cifrar_y_descifrar_para_alguien(tmp_path):
    llavero = tmp_path / "gnupg"
    llavero.mkdir(mode=0o700)
    env = {"GNUPGHOME": str(llavero)}
    subprocess.run(["gpg", "--batch", "--passphrase", "", "--quick-gen-key", "prueba@muyu.test", "default", "default", "never"],
                   env={**os.environ, **env}, capture_output=True, check=True, timeout=120)
    archivo = tmp_path / "secreto.txt"
    archivo.write_text("muy secreto")
    plan = sistema.preparar(_sector(sistema, [archivo], "Cifrar para…"), {"destinatario": "prueba@muyu.test"}, [str(archivo)])
    assert _correr(plan, **env).returncode == 0 and (tmp_path / "secreto.txt.gpg").is_file()
    cifrado = tmp_path / "secreto.txt.gpg"
    plan = sistema.preparar(_sector(sistema, [cifrado], "Descifrar"), {}, [str(cifrado)])
    assert _correr(plan, **env).returncode == 0
    assert (tmp_path / "secreto-2.txt").read_text() == "muy secreto"            # no pisa el original


def test_lo_interactivo_va_a_konsole(tmp_path):
    plan = sistema.preparar(_sector(sistema, [], "SSH…"), {"servidor": "ana@servidor"}, [])
    assert plan["terminal"] and "ssh ana@servidor" in plan["argv"][-1]
    plan = sistema.preparar(_sector(sistema, [tmp_path], "Servidor HTTP"), {"puerto": 8123}, [str(tmp_path)])
    assert plan["terminal"] and "http.server 8123" in plan["argv"][-1] and plan["cwd"] == str(tmp_path)


# --- studios ---------------------------------------------------------------------------------------------------------


def test_studios_ofrece_segun_lo_que_hay(tmp_path):
    tex = tmp_path / "doc.tex"
    tex.write_text("\\documentclass{article}\\begin{document}Hola\\end{document}")
    assert {"Compilar", "Compilar con Biber", "Limpiar auxiliares"} <= {o["etiqueta"] for o in studios.opciones([str(tex)])}
    (tmp_path / "_quarto.yml").write_text("project: {type: website}\n")
    de_carpeta = {o["etiqueta"] for o in studios.opciones([str(tmp_path)])}
    assert {"Contar tipos", "Árbol", "Renderizar sitio", "Reparar YAML"} <= de_carpeta
    generales = studios.opciones([])
    assert {"Huella: objetivos", "Repos: estado", "Blog nuevo…"} <= {o["etiqueta"] for o in generales}
    assert all(o["sin_archivos"] and o["anillo"] == "interior" for o in generales)


@pytest.mark.skipif(not (rutas.proyecto("filesystem-studio") / "script_count_files_by_extension" / "main.sh").is_file(),
                    reason="sin Filesystem Studio al lado")
def test_contar_con_filesystem_studio(tmp_path):
    for n in ("a.pdf", "b.pdf", "c.txt"):
        (tmp_path / n).write_text("x")
    r = _correr(studios.preparar(_sector(studios, [tmp_path], "Contar tipos"), {}, [str(tmp_path)]))
    assert r.returncode == 0 and "pdf" in r.stdout.lower()


@pytest.mark.skipif(not shutil.which("git"), reason="sin git")
def test_estado_de_un_repo(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / "x.txt").write_text("x")
    opciones = {o["etiqueta"] for o in studios.opciones([str(tmp_path)])}
    assert {"Estado git", "Traer", "Sincronizar…"} <= opciones
    r = _correr(studios.preparar(_sector(studios, [tmp_path], "Estado git"), {}, [str(tmp_path)]))
    assert r.returncode == 0 and "main" in r.stdout and "x.txt" in r.stdout           # también sin commits
    assert "Historial git" in {o["etiqueta"] for o in studios.opciones([str(tmp_path / "x.txt")])}

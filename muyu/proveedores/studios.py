"""El proveedor de los studios: las herramientas de Filesystem, Git, LaTeX, Quarto y Huella Studio, llamadas por la CLI
que cada una declara en su `suite.yml` (nunca importando su código). Ofrece según lo que haya en el centro:

- un `.tex`: compilar con LuaLaTeX (con Biber), limpiar los auxiliares (LaTeX Studio, `script_compilar_latex`);
- un `.qmd`: renderizarlo, reparar su YAML (Quarto Studio); una carpeta con `_quarto.yml`: renderizar el sitio, verlo,
  sus índices de contenido, reparar el YAML de todos sus `.qmd`;
- una carpeta: contar por extensión, el árbol, los hardlinks, crear carpetas en lote, duplicados a hardlinks
  (Filesystem Studio); si es un repo git: su estado, traer, sincronizarlo (Git Studio);
- un archivo dentro de un repo git: su historial;
- nada (la rueda vacía): las generales — Huella Studio por fases, el estado y la sincronización de todos los repos,
  los blogs de Quarto y un blog o un post nuevo.

Cada opción dice qué resulta (`resultado`: archivos nuevos en una carpeta, un informe con la salida, o nada) y las
interactivas o largas se abren en Konsole (`terminal`). Nada de lo de Huella se muestra fuera de su propia salida.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from muyu import rutas

NOMBRE = "studios"


def _script(proyecto: str, *partes: str) -> Path:
    return rutas.proyecto(proyecto).joinpath(*partes)


def _p(clave, etiqueta, tipo="texto", defecto=None, **kw) -> dict:
    return {"clave": clave, "etiqueta": etiqueta, "tipo": tipo, "defecto": defecto, "opciones": kw.pop("opciones", []),
            "ayuda": kw.pop("ayuda", ""), "obligatorio": kw.pop("obligatorio", False), **kw}


def _o(ident: str, etiqueta: str, titulo: str, descripcion: str, icono: str, requiere: list[Path | str],
       parametros: list[dict] | None = None, sin_archivos: bool = False) -> dict:
    faltan = [str(r) if isinstance(r, Path) else r for r in requiere
              if (isinstance(r, Path) and not r.exists()) or (isinstance(r, str) and not shutil.which(r))]
    return {"proveedor": NOMBRE, "operacion": f"studios:{ident}", "clave": f"studios|{ident}", "a": None,
            "etiqueta": etiqueta, "titulo": titulo, "descripcion": descripcion, "icono": icono, "params": {},
            "parametros": parametros or [], "pide": bool(parametros), "faltan": [Path(f).name for f in faltan],
            "sin_archivos": sin_archivos, "categoria": "Studios", "anillo": "interior" if sin_archivos else ""}


def _repo_de(ruta: Path) -> Path | None:
    for p in [ruta, *ruta.parents] if ruta.is_dir() else ruta.parents:
        if (p / ".git").exists():
            return p
    return None


def _sitio_quarto(ruta: Path) -> Path | None:
    for p in [ruta, *ruta.parents][:4] if ruta.is_dir() else list(ruta.parents)[:4]:
        if (p / "_quarto.yml").is_file():
            return p
    return None


LATEX = ("latex-studio", "script_compilar_latex", "main.sh")
QUARTO_BLOGS = ("quarto-studio", "backend", "script_blogs_manager", "main.sh")
QUARTO_YAML = ("quarto-studio", "backend", "script_format_yaml", "main.py")
QUARTO_INDICES = ("quarto-studio", "backend", "script_generador_publicacion_similar", "main.sh")
FS = {"contar": ("filesystem-studio", "script_count_files_by_extension", "main.sh"),
      "arbol": ("filesystem-studio", "script_proyect_tree", "main.sh"),
      "detectar": ("filesystem-studio", "script_hardlinks-detector", "main.sh"),
      "carpetas": ("filesystem-studio", "script_create_folders_batch", "main.sh"),
      "duplicados": ("filesystem-studio", "script_hardlinks-creator", "main.py")}
GIT_SYNC = ("git-studio", "script_git_sync_respos")
HUELLA = ("huella-studio", "main.sh")


def opciones(rutas_: list[str]) -> list[dict]:
    if any(r.startswith(("http://", "https://")) for r in rutas_):
        return []
    if not rutas_:
        return _generales()
    salida: list[dict] = []
    p = Path(rutas_[0])
    exts = {Path(r).suffix.lower() for r in rutas_}
    if exts == {".tex"}:
        latex = _script(*LATEX)
        salida += [_o("compilar", "Compilar", "Compilar con LuaLaTeX", "LuaLaTeX, las pasadas que hagan falta (LaTeX Studio)", "application-pdf", [latex, "lualatex"]),
                   _o("compilar_biber", "Compilar con Biber", "Compilar con LuaLaTeX y Biber", "Con la bibliografía (Biber)", "view-pim-journal", [latex, "lualatex", "biber"]),
                   _o("limpiar_latex", "Limpiar auxiliares", "Limpiar los auxiliares (.aux, .log, .bbl…)", "Deja el .tex y el PDF", "edit-clear", [latex])]
    if exts == {".qmd"}:
        salida += [_o("render_qmd", "Renderizar", "Renderizar con Quarto", "quarto render", "quarto", ["quarto"]),
                   _o("yaml_qmd", "Reparar YAML", "Reparar el bloque YAML (Quarto Studio)", "El delimitador --- y las líneas en blanco sobrantes",
                      "document-edit", [_script(*QUARTO_YAML)])]
    if len(rutas_) == 1 and p.is_dir():
        salida += [_o("contar", "Contar tipos", "Contar los archivos por extensión", "Con el tamaño de cada tipo y el ranking (Filesystem Studio)",
                      "view-statistics", [_script(*FS["contar"])]),
                   _o("arbol", "Árbol", "El árbol de carpetas (Markdown)", "Tres niveles, con las exclusiones de siempre (Filesystem Studio)",
                      "view-list-tree", [_script(*FS["arbol"])]),
                   _o("detectar", "Hardlinks", "Detectar los hardlinks", "Agrupados por inodo, con su reporte (Filesystem Studio)",
                      "edit-link", [_script(*FS["detectar"])]),
                   _o("carpetas", "Crear carpetas…", "Crear carpetas en lote", "Una por línea; se pueden anidar con / (Filesystem Studio)",
                      "folder-new", [_script(*FS["carpetas"])], [_p("lista", "Carpetas (una por línea)", "multilinea", obligatorio=True)]),
                   _o("duplicados", "Duplicados a hardlinks…", "Sustituir duplicados por hardlinks",
                      "Archivos de igual nombre y contenido (SHA-256): se simula primero (Filesystem Studio)", "edit-copy",
                      [_script(*FS["duplicados"])], [_p("nombre", "Nombre del archivo a buscar", obligatorio=True),
                                                     _p("aplicar", "Aplicar (sin esto, solo simula)", "casilla", False)])]
        sitio = _sitio_quarto(p)
        if sitio == p:
            salida += [_o("render_sitio", "Renderizar sitio", "Renderizar el sitio Quarto", "quarto render de toda la carpeta", "quarto", ["quarto"]),
                       _o("preview_sitio", "Vista previa", "Vista previa del sitio (en Konsole)", "quarto preview: se cierra con Ctrl+C", "view-preview", ["quarto"]),
                       _o("indices", "Índices", "Generar los índices de contenido", "_contenido_<subblog>.qmd con enlaces (Quarto Studio)",
                          "view-list-details", [_script(*QUARTO_INDICES)]),
                       _o("yaml_sitio", "Reparar YAML", "Reparar el YAML de todos sus .qmd", "Recursivo e idempotente (Quarto Studio)", "document-edit",
                          [_script(*QUARTO_YAML)])]
    repo = _repo_de(p) if len(rutas_) == 1 else None
    if repo is not None and p.is_dir() and repo == p:
        salida += [_o("git_estado", "Estado git", "Estado de este repositorio", "Rama, cambios y los últimos commits", "vcs-normal", ["git"]),
                   _o("git_traer", "Traer", "Traer los cambios (pull --ff-only)", "Solo si se puede sin fusionar", "vcs-pull", ["git"]),
                   _o("git_sincronizar", "Sincronizar…", "Sincronizar este repositorio (Git Studio)", "pull, commit de lo hecho y push",
                      "vcs-push", [_script(*GIT_SYNC, "sync.sh"), "git"], [_p("mensaje", "Mensaje del commit", "texto", "", obligatorio=True)])]
    elif repo is not None and p.is_file():
        salida.append(_o("git_historial", "Historial git", "Historial de este archivo", "Sus últimos 30 commits (git log --follow)", "vcs-commit", ["git"]))
    return salida


def _generales() -> list[dict]:
    huella = _script(*HUELLA)
    sync = _script(*GIT_SYNC, "sync.sh")
    salida = [
        _o("huella_objetivos", "Huella: objetivos", "Huella Studio: lo declarado (enmascarado)", "perfil/objetivos.yml", "security-medium", [huella], sin_archivos=True),
        _o("huella_auditorias", "Huella: auditorías", "Huella Studio: las auditorías hechas", "Las carpetas de resultados y sus hallazgos", "view-list-text", [huella], sin_archivos=True),
        _o("huella_fase", "Huella: una fase…", "Huella Studio: correr una fase",
           "Simula; con «Aplicar», en Konsole (consulta la red)", "edit-find", [huella],
           [_p("fase", "Fase", "opcion", "fase0", opciones=[["fase0", "0 · preparación"], ["fase12", "1-2 · dorks, usuarios y correos"],
                                                            ["fase34", "3-4 · repos y secretos"], ["fase5", "5 · dominio"]]),
            _p("aplicar", "Aplicar (sin esto, solo dice qué haría)", "casilla", False)], sin_archivos=True),
        _o("git_todos", "Repos: estado", "Git Studio: el estado de todos los repositorios", "Los de repos-config.yml, de los últimos 30 días", "vcs-normal",
           [_script(*GIT_SYNC, "status.sh")], sin_archivos=True),
        _o("git_comprobar", "Repos: comprobar", "Git Studio: qué sincronizaría", "sync.sh --check (no escribe)", "vcs-update-required", [sync], sin_archivos=True),
        _o("blogs", "Blogs", "Quarto Studio: los blogs", "La lista del hub y sus pubs", "quarto", [_script(*QUARTO_BLOGS)], sin_archivos=True),
        _o("post_nuevo", "Post nuevo…", "Quarto Studio: un post nuevo (asistente, en Konsole)", "En el blog que se elija", "document-new",
           [_script(*QUARTO_BLOGS)], [_p("blog", "Blog", obligatorio=True)], sin_archivos=True),
        _o("blog_nuevo", "Blog nuevo…", "Quarto Studio: un blog nuevo", "La carpeta pub_<nombre> con su estructura", "folder-new",
           [_script(*QUARTO_BLOGS)], [_p("nombre", "Nombre (sin pub_)", obligatorio=True), _p("titulo", "Título", "texto", "")], sin_archivos=True),
    ]
    return salida


def preparar(s: dict, params: dict, archivos: list[str]) -> dict:
    """{argv, cwd, resultado, carpeta, terminal, mantener} para la ventana."""
    op = s["operacion"].split(":", 1)[1]
    p = Path(archivos[0]) if archivos else None
    carpeta = str(p if p and p.is_dir() else p.parent) if p else ""
    sh = lambda *partes: ["bash", str(_script(*partes))]  # noqa: E731
    if op in ("compilar", "compilar_biber"):
        return {"argv": sh(*LATEX) + ["-e", "lualatex"] + (["--biber"] if op == "compilar_biber" else []) + [str(p.with_suffix(""))],
                "cwd": carpeta, "resultado": "archivos", "carpeta": carpeta}
    if op == "limpiar_latex":
        return {"argv": sh(*LATEX) + ["--limpiar", str(p.with_suffix(""))], "cwd": carpeta, "resultado": "nada"}
    if op == "render_qmd":
        return {"argv": ["quarto", "render", str(p)], "cwd": carpeta, "resultado": "archivos", "carpeta": carpeta}
    if op == "yaml_qmd":
        return {"argv": ["python3", str(_script(*QUARTO_YAML)), "--file", str(p)], "resultado": "informe"}
    if op == "yaml_sitio":
        return {"argv": ["python3", str(_script(*QUARTO_YAML)), "--directory", str(p), "--recursive"], "resultado": "informe"}
    if op == "render_sitio":
        return {"argv": ["quarto", "render", str(p)], "cwd": str(p), "resultado": "informe"}
    if op == "preview_sitio":
        return {"argv": ["quarto", "preview", str(p)], "cwd": str(p), "terminal": True, "mantener": True}
    if op == "indices":
        return {"argv": sh(*QUARTO_INDICES) + [str(p)], "resultado": "archivos", "carpeta": str(p)}
    if op == "contar":
        return {"argv": sh(*FS["contar"]) + ["-t", "15", "--no-color", str(p)], "resultado": "informe"}
    if op == "arbol":
        return {"argv": sh(*FS["arbol"]) + ["-f", "md", "-L", "3"], "cwd": str(p), "resultado": "archivos", "carpeta": str(p)}
    if op == "detectar":
        return {"argv": sh(*FS["detectar"]) + [str(p), "--report"], "resultado": "informe"}
    if op == "carpetas":
        lista = Path(tempfile.mkstemp(prefix="muyu-carpetas-", suffix=".txt")[1])
        lista.write_text(params.get("lista", "").strip() + "\n", encoding="utf-8")
        return {"argv": sh(*FS["carpetas"]) + ["-y", "-f", str(lista), "-p", str(p)], "resultado": "nada"}
    if op == "duplicados":
        return {"argv": ["python3", str(_script(*FS["duplicados"])), params["nombre"], "-d", str(p)]
                + ([] if params.get("aplicar") else ["--dry-run"]) + (["--auto"] if params.get("aplicar") else []), "resultado": "informe"}
    if op == "git_estado":
        return {"argv": ["sh", "-c", 'git -C "$1" status -sb && echo && { git -C "$1" log --oneline -12 2>/dev/null || echo "(sin commits todavía)"; }',
                         "git", str(p)], "resultado": "informe"}
    if op == "git_traer":
        return {"argv": ["git", "-C", str(p), "pull", "--ff-only"], "resultado": "informe"}
    if op == "git_sincronizar":
        return {"argv": sh(*GIT_SYNC, "sync.sh") + ["-m", params["mensaje"], "-r", p.name], "resultado": "informe"}
    if op == "git_historial":
        return {"argv": ["git", "-C", str(p.parent), "log", "--follow", "-n", "30", "--format=%h  %ad  %s", "--date=short", "--", p.name],
                "resultado": "informe"}
    if op == "huella_objetivos":
        return {"argv": sh(*HUELLA) + ["objetivos"], "resultado": "informe"}
    if op == "huella_auditorias":
        return {"argv": sh(*HUELLA) + ["auditorias"], "resultado": "informe"}
    if op == "huella_fase":
        orden = sh(*HUELLA) + [params.get("fase") or "fase0"]
        if params.get("aplicar"):
            return {"argv": orden + ["--aplicar"], "terminal": True, "mantener": True}
        return {"argv": orden, "resultado": "informe"}
    if op == "git_todos":
        return {"argv": sh(*GIT_SYNC, "status.sh") + ["--days", "30"], "resultado": "informe"}
    if op == "git_comprobar":
        return {"argv": sh(*GIT_SYNC, "sync.sh") + ["--check"], "resultado": "informe"}
    if op == "blogs":
        return {"argv": sh(*QUARTO_BLOGS) + ["list"], "resultado": "informe"}
    if op == "post_nuevo":
        return {"argv": sh(*QUARTO_BLOGS) + ["new-post", params["blog"]], "terminal": True, "mantener": True}
    if op == "blog_nuevo":
        return {"argv": sh(*QUARTO_BLOGS) + ["init-blog", params["nombre"]] + ([params["titulo"]] if params.get("titulo") else []),
                "resultado": "informe"}
    raise LookupError(f"Los studios no saben «{op}».")
